import sys
import os
import time

# -------------------------------------------------------------------------
# 🔧 PATHING FIX
# -------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR) 

# -------------------------------------------------------------------------
# 📦 IMPORTS
# -------------------------------------------------------------------------
try:
    print("⏳ Linking up with the src folder...")
    from src.cloud import CloudManager 
    from src.broker import BrokerAPI 
    from src.strategy import Strategy
    print("✅ Imports secure.")
except ImportError as e:
    print(f"\n💀 CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# -------------------------------------------------------------------------
# 🚀 MAIN LOGIC
# -------------------------------------------------------------------------
def main():
    print("\n" + "="*50)
    print("✨  INITIALIZING TRADING CLOUD INFRASTRUCTURE  ✨")
    print("="*50)
    
    print("\n🏗️  Constructing objects...")
    try:
        my_cloud = CloudManager()
        print(f"   ☁️  Cloud Sync -> [OK] (Balance: ${my_cloud.state.get('current_balance', 0)})")

        my_broker = BrokerAPI()
        if my_broker.startup():
            print("   🏦 Broker Connection -> [ESTABLISHED]")
        else:
            print("   ❌ Broker Connection Failed. Retrying in loop...")
        
        my_strategy = Strategy()
        print("   🧠 Strategy Engine -> [ONLINE]")
        
    except Exception as e:
        print(f"📉 Crash during init: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n🚀 All systems nominal. Entering Main Loop...")
    print("📈 Volatility is looking spicy today. Let's catch some pips.\n")

    try:
        while True:
            # 1. Update Connection & Time
            if not my_broker.connected:
                print("⚠️ Broker disconnected. Reconnecting...")
                if my_broker.startup():
                    print("✅ Reconnected!")
                else:
                    time.sleep(5)
                    continue

            server_time = my_broker.get_server_time_iso()
            print(f"\n⏰ Tick: {server_time} | Active Pairs: {len(my_cloud.state.get('active_pairs', []))}")

            # 2. Iterate Portfolio
            for pair in my_cloud.state.get('active_pairs', []):
                try:
                    signal, sl, tp, comment = my_strategy.analyze(pair, my_broker, my_cloud)

                    if signal:
                        print(f"   🚨 SIGNAL FOUND on {pair}: {signal} (SL: {sl:.5f} | TP: {tp:.5f})")
                        volume = 0.01 
                        result = my_broker.execute_trade(pair, signal, volume, sl, tp, comment)
                        
                        if result:
                            print(f"   ✅ Trade Executed! Ticket: {result.order}")
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
                                'exit_price': 0,
                                'pnl': 0,
                                'spread': my_broker.get_spread(pair)
                            }
                            my_cloud.log_trade(trade_data)
                except Exception as e:
                    print(f"   ❌ Error processing {pair}: {e}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Manual Shutdown Triggered.")
    except Exception as e:
        print(f"📉 Critical Runtime Crash: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print("😴 Session ended. Go touch grass.")
    print("="*50)

if __name__ == "__main__":
    main()
