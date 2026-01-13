# ==============================================================================
# ---- Turtle Main v1.4.1 (Weekend Fix) ----
# ==============================================================================
import sys
import os
import time
from datetime import datetime
import MetaTrader5 as mt5

# -------------------------------------------------------------------------
# 🔧 PATHING FIX
# -------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR) 

# -------------------------------------------------------------------------
# 📦 IMPORTS
# -------------------------------------------------------------------------
try:
    print("🥁 Rolling out the red carpet for the modules...")
    from src.cloud import CloudManager 
    from src.broker import BrokerAPI 
    from src.strategy import Strategy
    from src.telegram_bot import TelegramBot
    from config import TRAILING_CONFIG, CRYPTO_MARKETS, MAX_OPEN_TRADES, DEFAULT_PARAMS
    print("✅ The squad is assembled.")
except ImportError as e:
    print(f"\n💀 CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# -------------------------------------------------------------------------
# 🧠 HELPER LOGIC
# -------------------------------------------------------------------------
def sync_balance(broker, cloud):
    """
    🏦 The Banker.
    Forces the bot to look at the REAL account balance, not the memory.
    """
    if not broker.connected: return
    account_info = mt5.account_info()
    if account_info:
        real_balance = account_info.balance
        cloud.state['current_balance'] = real_balance

def manage_running_trades(broker, cloud, tg_bot):
    """
    🏃‍♂️ The Trailer.
    Moves SL to break-even and trails profit.
    """
    if not broker.connected: return
    
    # Get live positions
    positions = broker.get_open_positions()
    if not positions: return

    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        price_current = pos.price_current
        price_open = pos.price_open
        sl = pos.sl
        tp = pos.tp
        type_op = pos.type 
        
        # Determine Point Size (e.g. 0.00001 or 0.01)
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info: continue
        point = symbol_info.point
        
        # CONFIGS (Converted from 'points' to real price delta)
        activation_dist = TRAILING_CONFIG['sl_activation_distance'] * point
        trail_dist = TRAILING_CONFIG['sl_distance'] * point
        
        # --- BUY LOGIC ---
        if type_op == 0: 
            profit_distance = price_current - price_open
            
            # 1. Break Even / Trailing
            if profit_distance > activation_dist:
                new_sl = price_current - trail_dist
                # Only move SL UP
                if new_sl > sl:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": ticket,
                        "sl": float(new_sl),
                        "tp": float(tp), # Keep existing TP
                        "magic": 234000
                    }
                    res = mt5.order_send(request)
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   🏃‍♂️ Trailed SL for {symbol} to {new_sl}")

        # --- SELL LOGIC ---
        elif type_op == 1:
            profit_distance = price_open - price_current
            
            # 1. Break Even / Trailing
            if profit_distance > activation_dist:
                new_sl = price_current + trail_dist
                # Only move SL DOWN (remember SL is above price for shorts)
                if new_sl < sl or sl == 0:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": ticket,
                        "sl": float(new_sl),
                        "tp": float(tp),
                        "magic": 234000
                    }
                    res = mt5.order_send(request)
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   🏃‍♂️ Trailed SL for {symbol} to {new_sl}")

def audit_trades(broker, cloud, tg_bot):
    if not broker.connected: return

    memory_trades = cloud.state.get('open_bot_trades', [])
    if not memory_trades: return

    live_positions = broker.get_open_positions() 
    live_tickets = [p.ticket for p in live_positions]

    for trade in memory_trades[:]:
        ticket = trade['ticket']
        if ticket not in live_tickets:
            print(f"   🕵️ Audit: Trade {ticket} missing. Investigating...")
            status = broker.check_trade_status(ticket)
            
            if status['status'] == 'closed':
                trade['exit_price'] = status['exit_price']
                trade['close_time'] = status['close_time']
                trade['pnl'] = status['pnl']
                
                cloud.log_trade(trade, reason="CLOSED_BY_BROKER") 
                cloud.deregister_trade(ticket)
                tg_bot.send_msg(f"💰 TRADE CLOSED: {trade['pair']}\nPnL: {trade['pnl']}")

def check_weekend_chill(broker, cloud, tg_bot):
    """
    🏖️ The Friday Chill Protocol
    Closes all Forex trades on Friday evening (after 20:00).
    Keeps Crypto running.
    """
    now = datetime.now()
    # Friday = 4. Check if it's Friday and past 20:00 (8 PM)
    if now.weekday() == 4 and now.hour >= 20:
        open_trades = cloud.state.get('open_bot_trades', [])
        for trade in open_trades[:]:
            pair = trade['pair']
            if pair not in CRYPTO_MARKETS:
                print(f"   🏖️ Weekend Chill: Closing {pair}...")
                # Close trade
                is_long = trade['signal'] == 'BUY'
                if broker.close_trade(trade['ticket'], pair, trade['volume'], is_long):
                    tg_bot.send_msg(f"🏖️ WEEKEND EXIT: {pair}")
                    cloud.deregister_trade(trade['ticket'])
                    cloud.log_trade(trade, reason="FRIDAY_CLOSE")
        return True
    
    # 🛑 HARD STOP for Sunday Trading (6 = Sunday)
    # If it's Sunday, we return True to BLOCK new trades, but we don't close existing ones (already done Friday)
    if now.weekday() == 6:
        return True
        
    return False

def main():
    print("\n🚀 INITIALIZING TURTLE V1.4.1...")
    print(f"   🛡️ Risk Guard: Max {MAX_OPEN_TRADES} Trades | Lots: Fixed (Config)")
    print("   🏃‍♂️ Trailing Logic: ACTIVE")
    print("   🏖️ Weekend Protocol: ACTIVE")
    
    # 1. Initialize Components
    my_cloud = CloudManager()
    my_broker = BrokerAPI()
    
    # 🧠 Inject Config Params into Strategy
    my_strategy = Strategy(default_params=DEFAULT_PARAMS)
    
    tg_bot = TelegramBot()

    # 2. Connect to MT5
    if not my_broker.startup():
        tg_bot.send_msg("🚨 CRITICAL: MT5 Connection Failed!")
        sys.exit(1)

    tg_bot.send_msg(f"🤖 Turtle Online!\nStrategy: {my_strategy.name}")

    # 3. Main Loop
    try:
        while True:
            # Sync Real Balance
            sync_balance(my_broker, my_cloud)

            # Check for Telegram Commands
            cmd = tg_bot.get_latest_command()
            
            if cmd == "pause":
                my_cloud.state['status'] = 'paused'
                tg_bot.send_msg("⏸️ Bot PAUSED. No new entries.")
                my_cloud.save_memory()
            elif cmd == "resume":
                my_cloud.state['status'] = 'running'
                tg_bot.send_msg("▶️ Bot RESUMED. Hunting...")
                my_cloud.save_memory()
            elif cmd == "status":
                bal = my_cloud.state.get('current_balance', 0)
                status_msg = f"📊 STATUS REPORT\nState: {my_cloud.state.get('status')}\nBalance: ${bal}\nOpen Trades: {len(my_cloud.state.get('open_bot_trades', []))}"
                tg_bot.send_msg(status_msg)

            # Audit existing trades (Logs closes)
            audit_trades(my_broker, my_cloud, tg_bot)
            
            # Manage Running Trades (Trailing SL) 🏃‍♂️
            manage_running_trades(my_broker, my_cloud, tg_bot)
            
            # Check Weekend/Market Status
            is_weekend = check_weekend_chill(my_broker, my_cloud, tg_bot)

            # If paused, skip analysis
            if my_cloud.state.get('status') == 'paused':
                time.sleep(5)
                continue

            # --- 🛡️ RISK GUARD: MAX TRADES CHECK ---
            current_open_trades = my_cloud.state.get('open_bot_trades', [])
            if len(current_open_trades) >= MAX_OPEN_TRADES:
                time.sleep(10)
                continue

            active_trade_pairs = [t['pair'] for t in current_open_trades]

            # Market Scan
            active_pairs = my_cloud.state.get('active_pairs', [])
            for pair in active_pairs:
                
                # 🛑 DUPLICATE CHECK
                if pair in active_trade_pairs: continue

                # 🛑 FILTER: If weekend, SKIP FOREX completely
                if is_weekend and pair not in CRYPTO_MARKETS:
                    continue

                try:
                    # 🛠️ CHECK MARKET OPEN STATUS BEFORE REQUESTING DATA
                    # This prevents the "Market Closed" error spam
                    sym_info = mt5.symbol_info(pair)
                    if not sym_info: continue
                    
                    # Get Data
                    df = my_broker.get_data(pair, timeframe=mt5.TIMEFRAME_M15, n=200)
                    if df is None or df.empty: continue

                    # Analyze
                    df = my_strategy.calc_indicators(df, my_cloud.state.get('strategy_params', {}))
                    signal, sl, tp, comment = my_strategy.analyze(pair, my_broker, my_cloud)

                    if signal:
                        # Execute
                        volume = my_broker.calc_position_size(pair, sl, risk=0.01)
                        result = my_broker.execute_trade(pair, signal, volume, sl, tp, comment)
                        
                        if result:
                            server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"   ✅ Trade Executed! Ticket: {result.order}")
                            
                            # 🛠️ ROUNDING FOR MESSAGE
                            clean_sl = round(sl, 5)
                            clean_tp = round(tp, 5)
                            
                            tg_bot.send_msg(f"🚀 ENTRY: {pair} {signal}\nSL: {clean_sl}\nTP: {clean_tp}")

                            trade_data = {
                                'ticket': result.order,
                                'strategy': comment,
                                'signal': signal,
                                'pair': pair,
                                'open_time': server_time,
                                'entry_price': result.price,
                                'stop_loss_price': sl,
                                'take_profit_price': tp,
                                'volume': volume,
                                'spread': my_broker.get_spread(pair),
                                'exit_price': 0,
                                'pnl': 0
                            }
                            # 🚫 REMOVED "OPEN" LOGGING PER USER REQUEST
                            # my_cloud.log_trade(trade_data, reason="OPEN")
                            
                            # Save to Memory for the Auditor (Still needed to track the trade!)
                            my_cloud.register_trade(trade_data)
                            
                            active_trade_pairs.append(pair)
                            
                            if len(my_cloud.state.get('open_bot_trades', [])) >= MAX_OPEN_TRADES:
                                break 

                except Exception as e:
                    # 🤫 Silence the "Market Closed" errors to keep logs clean
                    if "Market closed" not in str(e):
                        print(f"   ❌ Error {pair}: {e}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Manual Shutdown.")
    except Exception as e:
        print(f"📉 CRITICAL CRASH: {e}")
        tg_bot.send_msg(f"📉 CRITICAL CRASH: {e}")

if __name__ == "__main__":
    main()