import sys
import time
import traceback
import asyncio
from datetime import datetime # 🛠️ FIX: Added missing import
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

    except Exception as e:
        print(f"Update Loop Error: {e}")

async def manage_trades():
    # Trade Management Logic
    pass

async def scan_market():
    # Market Scanning Logic
    if cloud.state['status'] != 'running': return

    pairs = cloud.state['active_pairs']
    for pair in pairs:
        print(f"🔎 Scanning {pair}...")
        signal, sl, tp, strat = generate_signal(pair, broker, cloud)
        
        if signal:
             # Execute
            res = broker.execute_trade(pair, signal, 0.01, sl, tp, strat)
            
            if res: # Only proceed if execution valid
                df = broker.fetch_candles(pair, '5m', 50)
                # 🛠️ FIX: Pass Price to Chart
                link = cloud.upload_chart(df, pair, signal, res.price)
                
                new_trade = {
                    'ticket': res.ticket, 'pair': pair, 'strategy': strat, 
                    'signal': signal, 'entry_price': res.price, 'sl': sl, 'tp': tp, 
                    'volume': 0.01, 'open_time': datetime.now().isoformat(), 
                    'trail_count': 0, 'screenshot': link, 
                    'take_profit_price': tp, 'stop_loss_price': sl, 'exit_price': 0
                }
                cloud.state['open_bot_trades'].append(new_trade)
                await bot.send_message(TELEGRAM_CHAT_ID, f"🚀 OPEN {signal} {pair}\nStrategy: {strat}\nEntry: {res.price:.5f}\n{link}")
                await asyncio.sleep(1)

async def main():
    global cloud, broker, bot
    print("🚀 MainFrame V3.1 (ACCOUNTANT) Waking Up...")
    try:
        cloud = CloudManager()
        broker = BrokerAPI()
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await process_updates()
        await manage_trades()
        await scan_market()
        
        cloud.save_state()
        print("💤 Going to sleep...")
        
    except Exception as e:
        print(f"CRITICAL CRASH: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())