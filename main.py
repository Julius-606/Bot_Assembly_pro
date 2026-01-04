import sys
import os
import time

# -------------------------------------------------------------------------
# 🔧 PATHING FIX: Ensure we can find 'src' and 'config.py'
# -------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR) 

# -------------------------------------------------------------------------
# 📦 IMPORTS (Corrected Class Names)
# -------------------------------------------------------------------------
try:
    print("⏳ Linking up with the src folder...")
    # NOTE: These names must match the classes in your files exactly!
    from src.cloud import CloudManager   # Was 'Cloud' (Incorrect)
    from src.broker import BrokerAPI     # Was 'Broker' (Incorrect)
    from src.strategy import Strategy    # We are creating this class now
    print("✅ Imports secure. We are liquidity rich.")
except ImportError as e:
    print(f"\n💀 CRITICAL IMPORT ERROR: {e}")
    print(f"❌ Make sure you have 'src/__init__.py' created!")
    sys.exit(1)

# -------------------------------------------------------------------------
# 🚀 MAIN LOGIC
# -------------------------------------------------------------------------
def main():
    print("\n" + "="*50)
    print("✨  INITIALIZING TRADING CLOUD INFRASTRUCTURE  ✨")
    print("="*50)
    
    # 1. Initialize Components
    print("\n🏗️  Constructing objects...")
    try:
        # Initialize the Cloud first to get settings/pairs
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

    # 3. Execution Loop
    try:
        while True:
            # 1. Update Connection & Time
            if not my_broker.connected:
                print("⚠️ Broker disconnected. Reconnecting...")
                my_broker.startup()
                time.sleep(5)
                continue

            server_time = my_broker.get_server_time_iso()
            print(f"\n⏰ Tick: {server_time} | Active Pairs: {len(my_cloud.state['active_pairs'])}")

            # 2. Iterate through your Portfolio
            for pair in my_cloud.state['active_pairs']:
                try:
                    # Analyze the market
                    # We pass broker/cloud so strategy can fetch candles and parameters
                    signal, sl, tp, comment = my_strategy.analyze(pair, my_broker, my_cloud)

                    if signal:
                        print(f"   🚨 SIGNAL FOUND on {pair}: {signal} (SL: {sl:.5f} | TP: {tp:.5f})")
                        
                        # Fetch risk parameters or use default volume
                        # TODO: Add dynamic lot size calculation in strategy or here
                        volume = 0.01 

                        # Execute Trade
                        result = my_broker.execute_trade(pair, signal, volume, sl, tp, comment)
                        
                        if result:
                            print(f"   ✅ Trade Executed! Ticket: {result.order}")
                            
                            # Log to Cloud
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
                            
                    else:
                        # Optional: Print something to show it's alive
                        # print(f"   💤 {pair}: No signal")
                        pass

                except Exception as e:
                    print(f"   ❌ Error processing {pair}: {e}")

            # 3. Sync State & Sleep
            # Don't spam the broker; sleep for a bit (e.g., 10 seconds or wait for next candle)
            time.sleep(10)
            
            # Simple heartbeat to save state to Drive periodically could go here
            # my_cloud.save_state()

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
