import sys
import os
import time
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
    from config import TRAILING_CONFIG, CRYPTO_MARKETS
    print("✅ The squad is assembled.")
except ImportError as e:
    print(f"\n💀 CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# -------------------------------------------------------------------------
# 🧠 HELPER LOGIC
# -------------------------------------------------------------------------
def audit_trades(broker, cloud, tg_bot):
    """
    The Auditor 🕵️‍♂️
    Checks Memory vs Reality.
    If a trade is in Memory but NOT in Open Positions, it closed.
    We verify the close reason and log it.
    """
    if not broker.connected: return

    memory_trades = cloud.state.get('open_bot_trades', [])
    if not memory_trades: return

    live_positions = broker.get_open_positions()
    live_tickets = [p.ticket for p in live_positions] if live_positions else []

    for trade in memory_trades:
        ticket = trade['ticket']
        
        # If ticket is missing from live positions, it's CLOSED
        if ticket not in live_tickets:
            print(f"   🔎 Auditing closed trade #{ticket}...")
            details = broker.check_trade_status(ticket)
            
            if details['status'] == 'closed':
                # Determine Reason
                comment = details.get('comment', '').lower()
                reason = "MANUAL/UNKNOWN"
                
                if "friday" in comment: reason = "FRIDAY CLOSE"
                elif "sl" in comment or "stop loss" in comment: reason = "SL HIT"
                elif "tp" in comment or "take profit" in comment: reason = "TP HIT"
                elif details['pnl'] > 0 and "sl" not in comment: reason = "PROFIT CLOSE" # Generic
                
                # Update PnL and Exit Price for the log
                trade['exit_price'] = details['exit_price']
                trade['close_time'] = details['close_time']
                trade['pnl'] = details['pnl']
                
                # Log the Exit
                cloud.log_trade(trade, reason=reason)
                
                # Remove from Memory
                cloud.close_trade_in_memory(ticket)
                
                # Notify
                emoji = "💰" if details['pnl'] > 0 else "🩸"
                tg_bot.send_msg(f"{emoji} TRADE CLOSED: {trade['pair']}\nReason: {reason}\nPnL: ${details['pnl']}")
                print(f"   🏁 Trade #{ticket} finalized. Reason: {reason} | PnL: {details['pnl']}")


def manage_current_trades(broker, tg_bot):
    """ Runner & Trailing Logic """
    positions = broker.get_open_positions()
    if positions is None: return

    cfg = TRAILING_CONFIG
    
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        order_type = pos.type 
        current_sl = pos.sl
        current_tp = pos.tp
        open_price = pos.price_open
        
        tick = broker.get_tick(symbol)
        if not tick: continue
        current_price = tick.bid if order_type == 0 else tick.ask 
        
        # 1. THE RUNNER (Dynamic TP)
        point = mt5.symbol_info(symbol).point
        if current_tp > 0: 
            dist_to_tp = abs(current_tp - current_price)
            if dist_to_tp <= (cfg['tp_proximity_threshold'] * point):
                extension = cfg['tp_extension'] * point
                new_tp = current_tp + extension if order_type == 0 else current_tp - extension
                broker.modify_position(ticket, current_sl, new_tp)
                tg_bot.send_msg(f"🏃 {symbol} is running! Pushed TP to {new_tp:.5f}")
                current_tp = new_tp 

        # 2. TRAILING STOP
        activation = cfg['sl_activation_distance'] * point
        trail = cfg['sl_trailing_dist'] * point
        new_sl = current_sl
        
        if order_type == 0: # BUY
            if (current_price - open_price) > activation:
                potential_sl = current_price - trail
                if potential_sl > current_sl: new_sl = potential_sl
        elif order_type == 1: # SELL
            if (open_price - current_price) > activation:
                potential_sl = current_price + trail
                if current_sl == 0 or potential_sl < current_sl: new_sl = potential_sl

        if new_sl != current_sl:
            if broker.modify_position(ticket, new_sl, current_tp):
                tg_bot.send_msg(f"⛓️ Trailed SL on {symbol} to {new_sl:.5f}")


def check_friday_closing(broker, tg_bot):
    """ Force Close Forex on Friday Night """
    dt = broker.get_server_datetime()
    # Friday = 4. 21:00 Server Time.
    if dt.weekday() == 4 and dt.hour >= 21:
        positions = broker.get_open_positions()
        if not positions: return
        
        for pos in positions:
            symbol = pos.symbol
            if symbol not in CRYPTO_MARKETS:
                print(f"   🍷 Closing {symbol} for the weekend.")
                is_long = (pos.type == 0)
                # We simply close it here. The 'audit_trades' function will catch 
                # the closure in the next loop, read the "Friday Close" comment, 
                # and log it properly.
                broker.close_trade(pos.ticket, symbol, pos.volume, is_long)

# -------------------------------------------------------------------------
# 🚀 MAIN LOOP
# -------------------------------------------------------------------------
def main():
    print("\n" + "="*50)
    print("✨  MONEY MAKER (LINUX EDITION) FINAL GENESIS  ✨")
    print("="*50)
    
    try:
        tg_bot = TelegramBot()
        tg_bot.send_msg("🤖 System Online. Genesis Complete.")

        my_cloud = CloudManager()
        print(f"   ☁️  Cloud Sync -> [OK] (Balance: ${my_cloud.state.get('current_balance', 0)})")

        my_broker = BrokerAPI()
        if my_broker.startup():
            print("   🏦 Broker Connection -> [ESTABLISHED]")
        else:
            print("   ❌ Broker Connection Failed. Retrying...")
            tg_bot.send_msg("⚠️ Broker connection failed on startup!")
        
        my_strategy = Strategy()
        print("   🧠 Strategy Engine -> [ONLINE]")
        
    except Exception as e:
        print(f"📉 Crash during init: {e}")
        return

    print("\n🚀 All systems nominal. Entering Main Loop...")

    try:
        while True:
            # 1. TELEGRAM
            cmd = tg_bot.get_latest_command()
            if cmd == "pause":
                my_cloud.state['status'] = "paused"
                tg_bot.send_msg("⏸️ Bot Paused.")
            elif cmd == "resume":
                my_cloud.state['status'] = "running"
                tg_bot.send_msg("▶️ Bot Resumed.")
            elif cmd == "status":
                bal = my_broker.get_balance() if my_broker.connected else 0
                tg_bot.send_msg(f"📊 Balance: ${bal:.2f}\nStatus: {my_cloud.state.get('status')}")

            # 2. AUDIT & MANAGE (Always run this, even if paused)
            if my_broker.connected:
                try:
                    # Check for closed trades and log them
                    audit_trades(my_broker, my_cloud, tg_bot)
                    # Manage running trades
                    manage_current_trades(my_broker, tg_bot)
                    # Check for weekend
                    check_friday_closing(my_broker, tg_bot)
                except Exception as e:
                    print(f"   ⚠️ Management Error: {e}")

            if my_cloud.state.get('status') == "paused":
                time.sleep(2)
                continue

            # 3. CONNECTION CHECK
            if not my_broker.connected:
                print("⚠️ Reconnecting...")
                if my_broker.startup(): 
                    print("✅ Reconnected!")
                else: 
                    time.sleep(5)
                    continue

            server_time = my_broker.get_server_time_iso()
            print(f"\n⏰ Tick: {server_time} | Watching {len(my_cloud.state.get('active_pairs', []))} Pairs")

            # 4. STRATEGY LOOP
            for pair in my_cloud.state.get('active_pairs', []):
                try:
                    signal, sl, tp, comment = my_strategy.analyze(pair, my_broker, my_cloud)

                    if signal:
                        print(f"   🚨 SIGNAL: {pair} {signal}")
                        volume = 0.01 
                        result = my_broker.execute_trade(pair, signal, volume, sl, tp, comment)
                        
                        if result:
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
