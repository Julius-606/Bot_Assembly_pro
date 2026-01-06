🐙 Money Maker (Trend Runner V3.0)

"Because sleeping is for people who don't like money."

Welcome to the Money Maker, a next-gen, cloud-native trading fortress. This isn't just a script; it's a modular algorithmic ecosystem designed to hunt trends on Forex and Crypto markets while you're busy living your best life (or debugging other code).

🌟 What Makes It Special?

☁️ Cloud Native: Persistence via Google Drive and logging via Google Sheets. It remembers its state even if the server explodes.

🐧 Linux Ready: Optimized for Headless VMs using Wine. It logs in automatically and enables Algo Trading without you lifting a finger.

📱 Telegram Command Center: Control your bot from the beach.

/pause: Freezes new entries (but manages open trades).

/resume: Back to the hunt.

/status: Instant PnL and position report.

🧠 Trend Runner Strategy: A sophisticated Hybrid Regime Filter using ADX, RSI, and ATR to distinguish between choppy noise and massive trend runs.

📜 The Architecture

src/ (The Engine Room)

broker.py: The diplomat. It speaks MetaTrader5 fluently, handling connections, logins, and order execution.

cloud.py: The accountant. Manages the JSON memory file and logs every single trade to Google Sheets for post-game analysis.

strategy.py: The brain. Calculates indicators (EMA, RSI, ATR) and decides when to pull the trigger.

telegram_bot.py: The messenger. Keeps you in the loop with real-time alerts.

🛠️ Setup & Deployment

Clone the Repo:

git clone [https://github.com/your-repo/money-maker-v3.git](https://github.com/your-repo/money-maker-v3.git)


Install Dependencies:

pip install -r requirements.txt


Config:

Open config.py and add your Google Cloud credentials JSON.

Ensure your MT5 Login/Pass is correct (supports FBS-Demo out of the box).

Run It:

python main.py


⚠️ Disclaimer

This software is for educational purposes. Trading financial markets involves risk. Don't trade with money you can't afford to lose, and definitely don't blame the bot if the market decides to do a backflip.

"May your PnL be green and your drawdowns be shallow." 🚀
