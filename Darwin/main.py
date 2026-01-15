# ==============================================================================
# ---- Trend Runner Main v2.4.0 (Slippery TP Edition) ----
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
    from src.coach import Coach # 🧢 The Boss
    # Added MAX_RISK_PCT to import
    from config import TRAILING_CONFIG, CRYPTO_MARKETS, MAX_OPEN_TRADES, DEFAULT_PARAMS, MAX_RISK_PCT
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
    1. Moves SL to break-even and trails profit (Locks in gains).
    2. Moves TP AWAY from price (Infinite upside).
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
        type_op = pos.type # 0=Buy, 1=Sell
        
        # Determine Point Size (e.g. 0.00001 or 0.01)
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info: continue
        point = symbol_info.point
        
        # CONFIGS (Converted from 'points' to real price delta)
        activation_dist = TRAILING_CONFIG['sl_activation_distance'] * point
        trail_dist = TRAILING_CONFIG['sl_distance'] * point
        
        # TP Chase Configs
        tp_prox_dist = TRAILING_CONFIG['tp_proximity_threshold'] * point
        tp_ext_dist = TRAILING_CONFIG['tp_extension'] * point
        
        # --- BUY LOGIC 📈 ---
        if type_op == 0: 
            profit_distance = price_current - price_open
            dist_to_tp = tp - price_current
            
            # A. TRAILING STOP LOSS (Defense)
            if profit_distance > activation_dist:
                new_sl = price_current - trail_dist
                # Only move SL UP
                if new_sl > sl:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": ticket,
                        "sl": float(new_sl),
                        "tp": float(tp), # Keep existing TP for now
                        "magic": 234000
                    }
                    mt5.order_send(request)
                    # print(f"   🏃‍♂️ Trailed SL UP for {symbol}")

            # B. TRAILING TAKE PROFIT (Offense - "You'll never catch me")
            if dist_to_tp < tp_prox_dist:
                new_tp = tp + tp_ext_dist
                print(f"   🎣 Moving TP AWAY for {symbol} (Chasing the run)...")
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": float(sl), # Keep existing SL
                    "tp": float(new_tp),
                    "magic": 234000
                }
                res = mt5.order_send(request)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    tg_bot.send_msg(f"🎣 TP CHASE: {symbol} extended to {new_tp}")

        # --- SELL LOGIC 📉 ---
        elif type_op == 1:
            profit_distance = price_open - price_current
            dist_to_tp = price_current - tp
            
            # A. TRAILING STOP LOSS (Defense)
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
                    mt5.order_send(request)
                    # print(f"   🏃‍♂️ Trailed SL DOWN for {symbol}")

            # B. TRAILING TAKE PROFIT (Offense - "You'll never catch me")
            if dist_to_tp < tp_prox_dist:
                new_tp = tp - tp_ext_dist
                print(f"   🎣 Moving TP AWAY for {symbol} (Chasing the drop)...")
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": float(sl), 
                    "tp": float(new_tp),
                    "magic": 234000
                }
                res = mt5.order_send(request)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    tg_bot.send_msg(f"🎣 TP CHASE: {symbol} extended to {new_tp}")

def audit_trades(broker, cloud, tg_bot):
    """
    Returns True if a trade was closed, False otherwise.
    """
    if not broker.connected: return False

    memory_trades = cloud.state.get('open_bot_trades', [])
    if not memory_trades: return False

    live_positions = broker.get_open_positions() 
    live_tickets = [p.ticket for p in live_positions]
    
    trade_closed_flag = False

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
                trade_closed_flag = True
    
    return trade_closed_flag

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
        return True # It IS Friday chill time
    return False

def main():
    print("\n🚀 INITIALIZING TREND RUNNER V2.4.0...")
    print(f"   🛡️ Risk Guard: Max {MAX_OPEN_TRADES} Trades | Lots: Fixed (Config)")
    print(f"   👮 Risk Police: Max Loss capped at {MAX_RISK_PCT*100}% per trade")
    print("   🏃‍♂️ Trailing Logic: ACTIVE (SL Lock + TP Chase)")
    print("   🏖️ Weekend Protocol: ACTIVE")
    
    # 1. Initialize Components
    my_cloud = CloudManager()
    my_broker = BrokerAPI()
    
    # 🧢 Initialize the Coach
    my_coach = Coach()
    
    # 🧠 Inject Config Params into Strategy
    # FIXED: No arguments passed here! Strategy is independent.
    my_strategy = Strategy()
    
    tg_bot = TelegramBot()

    # 2. Connect to MT5
    if not my_broker.startup():
        tg_bot.send_msg("🚨 CRITICAL: MT5 Connection Failed!")
        sys.exit(1)

    tg_bot.send_msg(f"🤖 Trend Runner Online!\nStrategy: {my_strategy.name}")

    # 3. Main Loop
    try:
        while True:
            # Sync Real Balance
            sync_balance(my_broker, my_cloud)

            # Check for Telegram Commands
            cmd = tg_bot.get_latest_command()
            
            if cmd == "pause":
                my_cloud.state['status'] = 'paused'
                tg_bot.send_msg("⏸️ Bot PAUSED. No new entries. (Managing existing trades)")
                my_cloud.save_memory()
            elif cmd == "resume":
                my_cloud.state['status'] = 'running'
                tg_bot.send_msg("▶️ Bot RESUMED. Hunting...")
                my_cloud.save_memory()
            elif cmd == "status":
                bal = my_cloud.state.get('current_balance', 0)
                active_count = len(my_cloud.state.get('open_bot_trades', []))
                status_msg = (
                    f"📊 STATUS REPORT\n"
                    f"State: {my_cloud.state.get('status')}\n"
                    f"Balance: ${bal}\n"
                    f"Open Trades: {active_count}\n"
                    f"Strategy: {my_strategy.name}"
                )
                tg_bot.send_msg(status_msg)

            # Audit existing trades (Logs closes)
            # If a trade closed, we wake up the Coach immediately 🧢
            if audit_trades(my_broker, my_cloud, tg_bot):
                print("   🧢 Trade Closed. Waking up the Coach...")
                my_coach.consult_oracle()
            
            # Manage Running Trades (Trailing SL) 🏃‍♂️
            manage_running_trades(my_broker, my_cloud, tg_bot)
            
            # Check Weekend Protocol
            is_weekend_chill = check_weekend_chill(my_broker, my_cloud, tg_bot)

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

                # 🏖️ WEEKEND FILTER: Skip Forex on Friday night
                if is_weekend_chill and pair not in CRYPTO_MARKETS:
                    continue

                try:
                    # Get Data
                    df = my_broker.get_data(pair, timeframe=mt5.TIMEFRAME_M15, n=200)
                    if df is None or df.empty: continue

                    # Analyze
                    df = my_strategy.calc_indicators(df)
                    signal, sl, tp, comment = my_strategy.analyze(pair, my_broker, my_cloud)

                    if signal:
                        # 1. Calc Basic Volume
                        volume = my_broker.calc_position_size(pair, sl, risk=0.01)
                        
                        # 2. 👮 RISK POLICE: Force SL to adhere to Max Risk %
                        current_balance = my_cloud.state.get('current_balance', 100) # Default 100 to be safe
                        risk_limit_usd = current_balance * MAX_RISK_PCT
                        
                        is_long = (signal == 'BUY')
                        
                        # Validate and possibly Adjust SL
                        new_sl, was_adjusted = my_broker.validate_sl_for_risk(
                            pair, is_long, df['close'].iloc[-1], sl, volume, risk_limit_usd
                        )
                        
                        if was_adjusted:
                            print(f"   👮 Risk Police: Tightened SL for {pair} to limit loss to ${risk_limit_usd:.2f}")
                            
                            # Safety check: Is SL inside the spread?
                            tick = mt5.symbol_info_tick(pair)
                            current_price = tick.ask if is_long else tick.bid
                            dist = abs(current_price - new_sl)
                            spread_val = tick.ask - tick.bid
                            
                            # If New SL is dangerously close (less than 2x spread), abort trade
                            if dist < (spread_val * 2):
                                print(f"   🚫 Trade Aborted: Forced SL is too close to spread.")
                                continue
                                
                            sl = new_sl # Apply the new SL

                        # Execute
                        result = my_broker.execute_trade(pair, signal, volume, sl, tp, comment)
                        
                        if result:
                            server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"   ✅ Trade Executed! Ticket: {result.order}")
                            
                            # 🛠️ ROUNDING FOR MESSAGE
                            clean_sl = round(sl, 5)
                            clean_tp = round(tp, 5)
                            
                            tg_bot.send_msg(f"🚀 ENTRY: {pair} {signal}\nSL: {clean_sl}\nTP: {clean_tp}\n🧪 {my_strategy.name}")

                            # Capture spread at Open
                            spread_at_open = my_broker.get_spread(pair)

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
                                'spread': spread_at_open, # 📝 Log Spread here
                                'exit_price': 0,
                                'pnl': 0
                            }
                            # Log Entry (Memory Only now)
                            my_cloud.log_trade(trade_data, reason="OPEN")
                            # Save to Memory for the Auditor
                            my_cloud.register_trade(trade_data)
                            
                            active_trade_pairs.append(pair)
                            
                            if len(my_cloud.state.get('open_bot_trades', [])) >= MAX_OPEN_TRADES:
                                break 

                except Exception as e:
                    print(f"   ❌ Error {pair}: {e}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Manual Shutdown.")
    except Exception as e:
        print(f"📉 CRITICAL CRASH: {e}")
        tg_bot.send_msg(f"📉 CRITICAL CRASH: {e}")

if __name__ == "__main__":
    main()