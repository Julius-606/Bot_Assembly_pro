🐙 Money Maker Algo Suite

"Because sleeping is for people who don't like money."

Welcome to the Money Maker Suite, a modular, cloud-native algorithmic trading ecosystem designed for MetaTrader 5. This repository houses multiple autonomous trading bots, each running its own unique strategy while sharing a common robust infrastructure.

📂 Repository Structure

The suite is organized by strategy. Each folder is a self-contained bot instance.

Bot_Assembly_pro/
│
├── requirements.txt       # Global dependencies for all bots
├── README.md              # You are here
├── .gitignore             # Security rules (Ignores logs, creds, memory)
│
├── Trend_Runner/          # 🏃‍♂️ STRATEGY 1: Trend Following
│   ├── main.py            # Entry point
│   ├── config.py          # Settings & Credentials
│   └── src/               # Core Logic (Broker, Cloud, Strategy)
│
└── Turtle/                # 🐢 STRATEGY 2: Donchian Breakout
    ├── main.py            # Entry point
    ├── config.py          # Settings & Credentials
    └── src/               # Core Logic (Broker, Cloud, Strategy)


🌟 Core Features (Shared)

☁️ Cloud Native: Persistence via Google Drive and logging via Google Sheets.

🛡️ Risk Guard: Built-in protection against over-trading (MAX_OPEN_TRADES) and account blowouts (FIXED_LOT_SIZE).

📱 Telegram Command Center: Individual control for each bot.

/assemble: Global status report.

/trendrunner [pause/resume]: Controls Trend Runner.

/turtle [pause/resume]: Controls Turtle.

🚀 Strategies

1. Trend Runner (Trend_Runner/)

Type: Hybrid Regime Filter (Trend Following)

Logic: Uses EMA 200 for trend direction, RSI for momentum, and a Recent High/Low breakout confirmation.

Best For: Strong trending markets (Forex/Crypto).

Timeframe: M15

2. The Turtle (Turtle/)

Type: Classic Donchian Channel Breakout (System 1 Modified)

Logic: Enters when price breaks the 20-period High/Low. Filtered by EMA 50 to ensure we trade with the trend.

Best For: Catching massive breakouts early.

Timeframe: M15

🛠️ Setup & Deployment

Environment:
Ensure you have Python 3.10+ and MetaTrader 5 installed.

pip install -r requirements.txt


Configuration:

Trend Runner: Edit Trend_Runner/config.py. Update MT5_PATH and GOOGLE_CREDS.

Turtle: Edit Turtle/config.py. Update MT5_PATH and GOOGLE_CREDS.

Running the Bots:
You can run them in separate terminals:

Terminal A (Trend Runner):

cd Trend_Runner
python main.py


Terminal B (Turtle):

cd Turtle
python main.py


⚠️ Disclaimer
