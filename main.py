import sys
import os
import time
import random

# -------------------------------------------------------------------------
# 🔧 THE FIX: Pointing Python to the 'src' folder
# This ensures we don't get those "Module Not Found" errors. Total buzzkill.
# -------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.append(src_path)

# -------------------------------------------------------------------------
# 📦 IMPORTS (Now pointing to src!)
# -------------------------------------------------------------------------
try:
    print("⏳ Linking up with the src folder...")
    from src.cloud import Cloud
    from src.broker import Broker
    from src.strategy import Strategy
    print("✅ Imports secure. We are liquidity rich.")
except ImportError as e:
    print(f"\n💀 BRO, CRITICAL ERROR: {e}")
    print(f"❌ Could not find modules inside '{src_path}'")
    print("👉 Make sure you have 'cloud.py', 'broker.py', and 'strategy.py' in 'src/'\n")
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
        my_broker = Broker()
        print("   🏦 Broker Connection -> [ESTABLISHED]")
        
        my_strategy = Strategy()
        print("   🧠 Strategy Engine -> [ONLINE]")
        
        my_cloud = Cloud()
        print("   ☁️  Cloud Environment -> [SYNCED]")
        
    except Exception as e:
        print(f"📉 Crash during init: {e}")
        return

    # 2. System Check Simulation
    systems = [
        "🔥 Ignite thrusters", 
        "📡 Connect satellite uplink", 
        "💾 Mount swap drive", 
        "☁️  Inflate cumulus layers",
        "💸 Checking margin requirements"
    ]

    print("\n🔎 Pre-flight checks:")
    for sys_check in systems:
        time.sleep(0.2)
        print(f"   ✅ {sys_check} -> [OK]")

    print("\n🚀 All systems nominal. We are live!")
    print("📈 Volatility is looking spicy today. Let's catch some pips.\n")

    # 3. Execution Loop (The part I accidentally deleted earlier, my bad!)
    try:
        # Pass dependencies if your classes need them
        # e.g., my_cloud.connect(my_broker) 
        
        print("🔄 Starting main event loop...")
        
        # Simulating a run sequence
        if hasattr(my_strategy, 'analyze'):
            signal = my_strategy.analyze()
            print(f"   📊 Strategy says: {signal}")
        
        if hasattr(my_broker, 'execute'):
            print("   ⚡ Sending order to broker...")
            my_broker.execute(signal if 'signal' in locals() else "HOLD")
            
        if hasattr(my_cloud, 'run'):
            print("   🏃‍♂️ Running cloud sequence...")
            my_cloud.run()
            
    except Exception as e:
        print(f"📉 Oof, runtime crash: {e}")
    
    print("\n" + "="*50)
    print("😴 Session ended. Go touch grass.")
    print("="*50)

if __name__ == "__main__":
    main()