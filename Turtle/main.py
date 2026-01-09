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
    # Added MAX_OPEN_TRADES for the Risk Guard 🛡️
    from config import TRAILING_CONFIG, CRYPTO_MARKETS, MAX_OPEN_TRADES
    print("✅ The squad is assembled.")
except ImportError as e:
    print(f"\n💀 CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# -------------------------------------------------------------------------
# 🧠 HELPER LOGIC
# -------------------------------------------------------------------------
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

def main():
    print("\n🚀 INITIALIZING TURTLE V1.0...")
    print(f"   🛡️ Risk Guard: Max {MAX_OPEN_TRADES} Trades | Lots: Fixed (Config)")
    
    # 1. Initialize Components
    my_cloud = CloudManager()
    my_broker = BrokerAPI()
    my_strategy = Strategy()
    tg_bot = TelegramBot()

    # 2. Connect to MT5
    if not my_broker.startup():
        tg_bot.send_msg("🚨 CRITICAL: MT5 Connection Failed!")
        sys.exit(1)

    tg_bot.send_msg(f"🤖 Turtle Online!\nStrategy: {my_strategy.name}")

    # 3. Main Loop
    try:
        while True:
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
                status_msg = f"📊 STATUS REPORT\nState: {my_cloud.state.get('status')}\nOpen Trades: {len(my_cloud.state.get('open_bot_trades', []))}"
                tg_bot.send_msg(status_msg)

            # Audit existing trades
            audit_trades(my_broker, my_cloud, tg_bot)

            # If paused, skip analysis
            if my_cloud.state.get('status') == 'paused':
                time.sleep(5)
                continue

            # --- 🛡️ RISK GUARD: MAX TRADES CHECK ---
            current_open_trades = my_cloud.state.get('open_bot_trades', [])
            if len(current_open_trades) >= MAX_OPEN_TRADES:
                # We are full, just wait.
                time.sleep(10)
                continue

            # List of pairs we are ALREADY trading to prevent duplicates
            active_trade_pairs = [t['pair'] for t in current_open_trades]

            # Market Scan
            active_pairs = my_cloud.state.get('active_pairs', [])
            for pair in active_pairs:
                
                # 🛑 DUPLICATE CHECK: Don't double dip!
                if pair in active_trade_pairs:
                    continue

                try:
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
                            tg_bot.send_msg(f"🚀 ENTRY: {pair} {signal}\nSL: {sl}\nTP: {tp}")

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
                            # Log Entry
                            my_cloud.log_trade(trade_data, reason="OPEN")
                            # Save to Memory for the Auditor
                            my_cloud.register_trade(trade_data)
                            
                            # Add to local list immediately to prevent double buy in same loop
                            active_trade_pairs.append(pair)
                            
                            # Re-check max trades immediately
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