**🐙 Money Maker (MainFrame V3.0)**

> "From Trade Executioner to Cloud Accountant."

Money Maker is a modular, cloud-native trading bot designed to run autonomously on GitHub Actions. It has evolved from a Windows-dependent script to a robust, API-first system that tracks trades, manages risk, and logs everything to the cloud.

📜 History

V1.0 (The Terminal Era): Dependent on terminal64.exe (MetaTrader 5). Windows only. Heavy resource usage.

V1.5 (Cloud Awakening): Migrated to API-based logic. Headless operation. GitHub Actions integration.

V2.0 (The CPA Update): Added sophisticated accounting, "Real Life" PnL tracking, and smart trailing stops.

V3.0 (Modular & Live): Fully modular code structure (src/), ImgBB integration for charts, and Real Market Data via Yahoo Finance.

🧠 Strategy & Logic

The bot uses a Hybrid Regime Filter powered by ADX:

Trending (ADX > 25): Deploys SR_TREND (Breakout) + SCALPER (MACD/EMA).

Ranging (ADX < 25): Deploys MEAN_REVERT (Bollinger Bands + RSI).

It features a "Time Traveler" logic to handle the latency of Cron jobs, checking historical price action to see if TP/SL levels were hit while it was "asleep."

🛠️ Tech Stack

Language: Python 3.10

Execution: GitHub Actions (Cron)

Data Source: Yahoo Finance (yfinance)

Storage: Google Sheets (State Persistence & Logging)

Visuals: ImgBB (Chart hosting)

Libraries: pandas, mplfinance, gspread, python-telegram-bot

🚀 Deployment

Clone the repository.

Add your google_creds.json content to config.py (or use GitHub Secrets).

Add your ImgBB API Key to config.py.

Push to main branch to activate the workflow.

⚠️ Warning: This bot is designed for educational and simulation purposes. Use at your own risk with real funds.
