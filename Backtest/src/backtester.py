from src.broker import BrokerAPI
from src.cloud import CloudManager
from src.strategy import Strategy
import pandas as pd

class BacktestEngine:
    """The Engine 🏎️. Iterates through history and asks the strategy 'What now?'."""
    def __init__(self):
        self.broker = BrokerAPI()
        self.cloud = CloudManager()
        self.strategy = Strategy()

    def run_show(self, pair, tf, start, end, concoction, progress_bar):
        # Update the recipe
        self.strategy.state['ACTIVE_CONCOCTION'] = concoction
        self.strategy.update_name()
        
        # Connect to MT5
        success, msg = self.broker.startup()
        if not success: return msg

        # Get the data
        df = self.broker.get_historical_data(pair, tf, start, end)
        if df is None: return f"❌ {pair}: No data found."

        results = []
        warmup = 200 # Indicators need history to 'warm up'
        
        if len(df) <= warmup:
            return f"❌ {pair}: Data too short for warmup."

        # The Sliding Window Loop
        for i in range(warmup, len(df)):
            window = df.iloc[:i+1].copy()
            
            # Use the backtest-specific analyzer (No broker calls inside!)
            signal, sl, tp, name = self.strategy.analyze_backtest(window)
            
            if signal:
                curr_bar = df.iloc[i]
                results.append([
                    str(curr_bar['time']), pair, tf, signal,
                    round(curr_bar['close'], 5), round(sl, 5), round(tp, 5), name
                ])
            
            if i % 50 == 0:
                progress_bar.progress((i - warmup) / (len(df) - warmup))

        if results:
            self.cloud.log_test_results(results)
            return f"✅ {pair}: {len(results)} signals logged to Google Sheets."
        
        return f"😴 {pair}: Finished, but no signals found."