import sys
import time
import traceback
import asyncio
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Import Modules
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DEFAULT_PARAMS
from cloud import CloudManager
from broker import BrokerAPI
from strategy import generate_signal

# Globals
cloud = None
broker = None
bot = None
# We store the last day we checked to detect "New Day/Monday" events
last_known_day = None 

# --- MANAGEMENT SETTINGS ---
BE_TRIGGER_R = 1.0  
TRAIL_TRIGGER_R = 1.5 
TRAIL_DIST_ATR = 2.0  
MAX_OPEN_TRADES = 5 

async def health_check():
    global last_known_day
    
    # 1. MT5 Connectivity
    if not broker.check_connection():
        print("⚠️ MT5 Connection Pulse: FLATLINE. Attempting Defib...")
        if broker.startup(): 
            print("✅ MT5 Revived!")
            try:
                # Switched to HTML to avoid Markdown parsing errors with special chars
                await bot.send_message(TELEGRAM_CHAT_ID, "♻️ <b>System Update:</b> Connection restored.", parse_mode='HTML')
            except: pass
        else:
            print("❌ Defib Failed. Will retry in 5s.")

    # 2. Market Open Detection (Monday)
    # 🕒 TIME SOURCE CHANGE: Using MT5 Server time, not local PC time
    server_time = broker.get_server_datetime()
    current_day = server_time.weekday()
    
    # Initialize if first run
    if last_known_day is None:
        last_known_day = current_day

    if current_day == 0 and last_known_day == 6:
        print("☕ MONDAY DETECTED (Server Time). Waking up market scanner.")
        try:
            await bot.send_message(TELEGRAM_CHAT_ID, "🔔 <b>MARKET OPEN!</b> \nRise and Grind! 🍞💸", parse_mode='HTML')
        except: pass
    
    last_known_day = current_day

async def process_updates():
    try:
        last_id = cloud.state.get('last_update_id', 0)
        updates = await bot.get_updates(offset=last_id + 1, timeout=0.5)
        
        for update in updates:
            cloud.state['last_update_id'] = update.update_id
            
            if update.message and update.message.text:
                text = update.message.text.upper().strip()
                print(f"📩 CMD: {text}")
                
                # 🛠️ COMMAND HANDLER
                if text == "/STATUS":
                    st = cloud.state['status']
                    tr = len(cloud.state['open_bot_trades'])
                    real_bal = broker.get_balance()
                    cloud.state['current_balance'] = real_bal
                    
                    mt5_status = "🟢 Connected" if broker.check_connection() else "🔴 Disconnected"
                    pair_count = len(cloud.state.get('active_pairs', []))

                    msg = (
                        f"🤖 <b>MainFrame V6.4 (Patched)</b>\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"📡 MT5: {mt5_status}\n"
                        f"🚦 Bot State: {st}\n"
                        f"💼 Open Trades: {tr}/{MAX_OPEN_TRADES}\n"
                        f"📊 Active Pairs: {pair_count}\n"
                        f"💰 Balance: ${real_bal:.2f}\n"
                        f"━━━━━━━━━━━━━━"
                    )
                    await bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode='HTML')
                    
                elif text == "/STOP":
                    cloud.state['status'] = 'stopped'
                    cloud.save_state()
                    await bot.send_message(TELEGRAM_CHAT_ID, "🛑 Bot Paused.")
                
                elif text == "/START":
                    cloud.state['status'] = 'running'
                    cloud.save_state()
                    await bot.send_message(TELEGRAM_CHAT_ID, "✅ Bot Streamer Active.")

                elif text == "/KILL":
                    cloud.save_state() 
                    await bot.send_message(TELEGRAM_CHAT_ID, "💀 <b>SYSTEM SHUTDOWN INITIATED</b>", parse_mode='HTML')
                    print("💀 KILL COMMAND RECEIVED. STATE SAVED. TERMINATING PROCESS.")
                    return False 

    except Exception as e:
        print(f"⚠️ Update Loop Warning: {e}")
    
    return True 

async def manage_trades():
    if not cloud.state.get('open_bot_trades'): return

    try:
        cloud.state['current_balance'] = broker.get_balance()
    except: pass
    
    updated_trades = []
    
    for trade in cloud.state['open_bot_trades']:
        ticket = trade.get('ticket')
        pair = trade.get('pair')
        
        if not ticket or not pair: continue

        # 1. CHECK STATUS
        trade_status = broker.check_trade_status(ticket)
        
        if trade_status is None:
            updated_trades.append(trade)
            continue

        if trade_status.get('status') == 'closed':
            # 🛑 Trade Closed
            pnl = trade_status.get('pnl', 0.0)
            exit_price = trade_status.get('exit_price', 0.0)
            close_time = trade_status.get('close_time', broker.get_server_time_iso())
            
            emoji = "🤑" if pnl > 0 else "💀"
            try:
                await bot.send_message(TELEGRAM_CHAT_ID, f"{emoji} CLOSED {pair}\nTicket: {ticket}\nPnL: ${pnl:.2f}\n(Broker Trigger)")
            except: pass
            
            trade['exit_price'] = exit_price
            trade['pnl'] = pnl
            trade['close_time'] = close_time
            trade['close_reason'] = "BROKER_SL_TP"
            
            cloud.log_trade(trade)
            continue
            
        elif trade_status.get('status') == 'unknown':
            updated_trades.append(trade)
            continue

        # 2. OPEN Trade Management (Trailing Stop Logic)
        tick = broker.get_tick(pair)
        if not tick:
            updated_trades.append(trade) 
            continue
            
        current_bid = tick.bid
        current_ask = tick.ask
        is_long = trade['signal'] == 'BUY'
        exit_price_now = current_bid if is_long else current_ask
        entry = trade.get('entry_price', 0.0)
        sl = trade.get('stop_loss_price', 0.0)
        tp = trade.get('take_profit_price', 0.0)
        
        # 🧠 CRITICAL FIX: Use Initial Risk for R-Calc, NOT current Risk
        # If we use current risk, when SL moves to BE, risk becomes 0 and R becomes Infinite.
        initial_risk = trade.get('initial_risk', abs(entry - sl))
        if initial_risk == 0: initial_risk = 0.0001
        
        # Calculate PnL Points
        if is_long:
            pnl_points = exit_price_now - entry
        else:
            pnl_points = entry - exit_price_now
        
        current_r = pnl_points / initial_risk
        
        new_sl = None

        # BE Logic
        if current_r >= BE_TRIGGER_R and trade['trail_count'] == 0:
            new_sl = entry
            print(f"🛡️ BE Trigger: Moving SL to Entry for {pair}")

        # Trailing Logic
        elif current_r >= TRAIL_TRIGGER_R:
            # We trail by keeping distance of X ATRs
            # Since we don't have live ATR here easily, we approximate using initial risk
            # Assuming Initial Stop was 2 ATR wide -> 1 ATR = Initial Risk / 2
            estimated_atr = initial_risk / 2.0 
            
            if is_long:
                potential_new_sl = exit_price_now - (estimated_atr * TRAIL_DIST_ATR)
                if potential_new_sl > sl: new_sl = potential_new_sl
            else:
                potential_new_sl = exit_price_now + (estimated_atr * TRAIL_DIST_ATR)
                if potential_new_sl < sl: new_sl = potential_new_sl
        
        # 3. PUSH UPDATE
        if new_sl:
            print(f"📡 Sending SL Update to Server: {pair} -> {new_sl:.5f}")
            if broker.modify_position(ticket, new_sl, tp):
                trade['stop_loss_price'] = new_sl
                trade['trail_count'] += 1
                try:
                    await bot.send_message(TELEGRAM_CHAT_ID, f"🛡️ SL Moved on Server: {pair}")
                except: pass
            else:
                print(f"❌ SL Update Failed for {pair}")
        
        updated_trades.append(trade)

    cloud.state['open_bot_trades'] = updated_trades
    cloud.save_state()

async def scan_market():
    if cloud.state['status'] != 'running': return

    pairs = cloud.state.get('active_pairs', [])
    
    # 🕒 TIME SOURCE CHANGE: Server Time
    now_server = broker.get_server_datetime()
    is_weekend = now_server.weekday() >= 5
    
    if is_weekend: 
        crypto_sigs = ['BTC', 'ETH', 'XRP', 'LTC', 'SOL', 'DOGE']
        pairs_to_scan = [p for p in pairs if any(sig in p for sig in crypto_sigs)]
    else:
        pairs_to_scan = pairs
    
    if len(pairs_to_scan) == 0:
        status = "WEEKEND MODE" if is_weekend else "NORMAL MODE"
        print(f"⚠️ SCANNING 0 PAIRS! ({status}) - Total Loaded: {len(pairs)}")
    else:
        print(f"🔎 Scanning {len(pairs_to_scan)} active pairs...")

    signals_found = 0 

    for pair in pairs_to_scan:
        try:
            signal, sl, tp, strat_name = generate_signal(pair, broker, cloud)
            
            if signal:
                signals_found += 1
                active_pairs_open = [t['pair'] for t in cloud.state.get('open_bot_trades', [])]
                if pair in active_pairs_open: continue
                if len(cloud.state.get('open_bot_trades', [])) >= MAX_OPEN_TRADES: continue 

                print(f"\n🚨 SIGNAL FOUND: {signal} {pair} via {strat_name}") 
                res = broker.execute_trade(pair, signal, 0.01, sl, tp, strat_name)
                
                if res:
                    server_time = broker.get_server_time_iso()
                    spread = broker.get_spread(pair)
                    entry_price = float(res.price)
                    
                    # 🧠 CRITICAL: Calculate Initial Risk here for future R-calcs
                    initial_risk = abs(entry_price - sl)
                    
                    new_trade = {
                        'ticket': res.ticket, 
                        'pair': pair, 
                        'strategy': strat_name, 
                        'signal': signal, 
                        'entry_price': entry_price, 
                        'sl': sl, 
                        'tp': tp, 
                        'initial_risk': initial_risk, # <--- SAVED FOR TRAILING LOGIC
                        'volume': 0.01, 
                        'spread': spread, 
                        'open_time': server_time, 
                        'trail_count': 0, 
                        'take_profit_price': tp, 
                        'stop_loss_price': sl, 
                        'exit_price': 0,
                        'close_time': None
                    }
                    cloud.state.setdefault('open_bot_trades', []).append(new_trade)
                    cloud.save_state()
                    try:
                        await bot.send_message(TELEGRAM_CHAT_ID, f"🚀 OPEN {signal} {pair}\nTicket: {res.ticket}")
                    except: pass
                    
        except Exception as e:
            print(f"\n⚠️ Scan Error ({pair}): {e}")

    if signals_found == 0 and len(pairs_to_scan) > 0:
        print(f"💤 Scanned {len(pairs_to_scan)} pairs. 0 Signals. Market is dry.")

async def main_loop():
    global cloud, broker, bot
    print("🚀 MainFrame V6.4 (Patched) Starting...")
    
    try:
        cloud = CloudManager()
        broker = BrokerAPI()
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
    except Exception as e:
        print(f"❌ CRITICAL INIT ERROR: {e}")
        traceback.print_exc()
        return

    if cloud.state.get('status') != 'running':
        print("🔌 Auto-Pilot Engaged: Forcing Status to RUNNING.")
        cloud.state['status'] = 'running'
        cloud.save_state()

    if not cloud.state.get('active_pairs'):
        print("\n⚠️ AMNESIA DETECTED: active_pairs is empty! Injecting defaults...")
        cloud.state['active_pairs'] = cloud.default_state['active_pairs']
        cloud.save_state()

    try:
        current_bal = cloud.state.get('current_balance', 0.0)
        # 🕒 TIME SOURCE CHANGE
        server_now = broker.get_server_datetime().strftime('%Y-%m-%d %H:%M')
        
        start_msg = (
            f"⚡ <b>SYSTEM ONLINE</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 {server_now} (Server Time)\n"
            f"💰 Balance: ${current_bal:.2f}\n"
            f"🏃 Mode: AUTO-RUN (Disconnect Proof)\n"
            f"👀 Watching Markets..."
        )
        await bot.send_message(TELEGRAM_CHAT_ID, start_msg, parse_mode='HTML')
    except Exception as e:
        print(f"⚠️ Failed to send startup msg: {e}")

    loop_count = 0

    while True:
        try:
            await health_check()
            should_continue = await process_updates()
            if should_continue is False: 
                print("🛑 Process Terminated via Telegram /KILL.")
                break 
            await manage_trades()
            if cloud.state.get('status') == 'running':
                await scan_market()
            
            loop_count += 1
            if loop_count % 12 == 0:
                print(f"\n💓 System Pulse: Active | Trades: {len(cloud.state.get('open_bot_trades', []))} | Bal: ${cloud.state.get('current_balance', 0.0):.2f}")

            await asyncio.sleep(5) 
            
        except Exception as e:
            print(f"\n⚠️ Loop Crash: {e}")
            traceback.print_exc() 
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("🛑 Shutting down (Keyboard)...")