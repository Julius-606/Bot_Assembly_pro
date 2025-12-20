import sys
import time
import traceback
import asyncio
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Import Modules
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.cloud import CloudManager
from src.broker import BrokerAPI
from src.strategy import generate_signal

# Globals
cloud = None
broker = None
bot = None

async def process_updates():
    """Reads Telegram commands."""
    try:
        updates = await bot.get_updates(offset=cloud.last_update_id + 1, timeout=1)
        for update in updates:
            cloud.last_update_id = update.update_id
            if update.message and update.message.text:
                text = update.message.text.upper().strip()
                print(f"📩 CMD: {text}")
                
                if text == "/STATUS":
                    st = cloud.state['status']
                    mode = cloud.state.get('active_strategy', 'Unknown')
                    tr = len(cloud.state['open_bot_trades'])
                    bal = cloud.state['current_balance']
                    await bot.send_message(TELEGRAM_CHAT_ID, f"🤖 V3.1 Accountant\nStat: {st}\nMode: {mode}\nTrades: {tr}\nBal: ${bal:.2f}")
                    
                elif text == "/STOP":
                    cloud.state['status'] = 'stopped'
                    await bot.send_message(TELEGRAM_CHAT_ID, "🛑 Bot Stopped.")
                
                elif text == "/START":
                    cloud.state['status'] = 'running'
                    await bot.send_message(TELEGRAM_CHAT_ID, "✅ Bot Resumed.")

    except Exception as e:
        print(f"Update Loop Error: {e}")

async def manage_trades():
    """Checks open trades for exit conditions (TP/SL)."""
    # Placeholder for trade management logic
    # In V3, we would loop through cloud.state['open_bot_trades'] here
    pass

async def scan_market():
    """Scans all pairs for new entry signals."""
    if cloud.state['status'] != 'running': return

    pairs = cloud.state['active_pairs']
    print(f"🔎 Scanning {len(pairs)} pairs...")
    
    for pair in pairs:
        try:
            print(f"🔎 Scanning {pair}...")
            
            # 🛠️ FIX: Don't pass 'strat' or 'state' explicitly. 
            # The Strategy module extracts them from the 'cloud' object.
            signal, sl, tp, strat_name = generate_signal(pair, broker, cloud)
            
            if signal:
                print(f"🚨 SIGNAL FOUND: {signal} on {pair} ({strat_name})")
                
                # Execute Trade (Paper or Real)
                res = broker.execute_trade(pair, signal, 0.01, sl, tp, strat_name)
                
                if res: # Only proceed if execution valid
                    # Fetch data for chart
                    df = broker.fetch_candles(pair, '5m', 50)
                    
                    # Upload Chart
                    link = cloud.upload_chart(df, pair, signal, res.price)
                    
                    # Log to Cloud Brain
                    new_trade = {
                        'ticket': res.ticket, 
                        'pair': pair, 
                        'strategy': strat_name, 
                        'signal': signal, 
                        'entry_price': res.price, 
                        'sl': sl, 
                        'tp': tp, 
                        'volume': 0.01, 
                        'open_time': datetime.now().isoformat(), 
                        'trail_count': 0, 
                        'screenshot': link, 
                        'take_profit_price': tp, 
                        'stop_loss_price': sl, 
                        'exit_price': 0
                    }
                    
                    cloud.state['open_bot_trades'].append(new_trade)
                    cloud.save_state() # Save immediately after trade
                    
                    # Notify Boss
                    await bot.send_message(
                        TELEGRAM_CHAT_ID, 
                        f"🚀 OPEN {signal} {pair}\nStrategy: {strat_name}\nEntry: {res.price:.5f}\nSL: {sl}\nTP: {tp}\n{link}"
                    )
                    
                    # Anti-Spam / Rate Limit
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"⚠️ Strategy Error ({pair}): {e}")
            # traceback.print_exc() # Uncomment to see deep details if it crashes again

async def main():
    global cloud, broker, bot
    print("🚀 MainFrame V3.1 (ACCOUNTANT) Waking Up...")
    try:
        # Initialize Core Systems
        cloud = CloudManager()
        broker = BrokerAPI()
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Run Routine
        await process_updates()
        await manage_trades()
        await scan_market()
        
        # Save Memory before death
        cloud.save_state()
        print("💾 State Saved to Cloud.")
        print("😴 Going to sleep...")
        
    except Exception as e:
        print(f"CRITICAL CRASH: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
