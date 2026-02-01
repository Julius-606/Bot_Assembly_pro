import pandas as pd
import numpy as np
from src.broker import BrokerAPI
from src.cloud import CloudManager
from src.strategy import Strategy
from config import HARDCODED_LOT_SIZE, CONTRACT_SIZE
from datetime import datetime

class BacktestEngine:
    """The Scientist 🧪. Handles simulation and coordinates the reporting."""
    def __init__(self):
        self.broker = BrokerAPI()
        self.cloud = CloudManager()
        self.strategy = Strategy()

    def startup(self):
        return self.broker.startup()

    def init_batch(self, pairs, tf, recipe, strictness, start_date, end_date):
        """Initializes the Batch with the correct column order for 'Batches' metadata."""
        batch_id = int(self.cloud.get_next_batch_id())
        
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        # Order: Batch no. | Date Range | Selected Pairs | TimeFrame | Strategy | Strictness
        metadata = [
            batch_id,
            date_range,
            ", ".join(pairs),
            tf,
            "+".join(recipe),
            str(strictness)
        ]
        self.cloud.log_batch_meta(metadata)
        self.cloud.create_batch_sheet(batch_id)
        return batch_id

    def run_show(self, batch_id, pair, tf_str, start_dt, end_dt, recipe, strictness, progress_bar):
        self.strategy.state['ACTIVE_CONCOCTION'] = recipe
        self.strategy.update_name()
        
        df = self.broker.get_historical_data(pair, tf_str, start_dt, end_dt)
        if df is None or len(df) < 300:
            return f"❌ {pair}: Not enough data."

        trades = []
        warmup, total_bars = 250, len(df)
        
        idx = warmup
        while idx < total_bars:
            window = df.iloc[:idx+1].copy()
            signal, sl_p, tp_p, strat_name = self.strategy.analyze_backtest(window, strictness)
            
            if signal:
                entry_bar = df.iloc[idx]
                entry_price, open_time = float(entry_bar['close']), str(entry_bar['time'])
                spread = int(entry_bar.get('spread', 0))
                
                sl_dist, tp_dist = abs(entry_price - sl_p), abs(tp_p - entry_price)
                sl_money = float(round(sl_dist * HARDCODED_LOT_SIZE * CONTRACT_SIZE, 2))
                tp_money = float(round(tp_dist * HARDCODED_LOT_SIZE * CONTRACT_SIZE, 2))
                
                exit_found = False
                for j in range(idx + 1, total_bars):
                    check_bar = df.iloc[j]
                    high, low = float(check_bar['high']), float(check_bar['low'])
                    
                    if (signal == 'BUY' and low <= sl_p) or (signal == 'SELL' and high >= sl_p):
                        exit_price, reason, close_t = float(sl_p), "SL Hit", str(check_bar['time'])
                        exit_found = True
                    elif (signal == 'BUY' and high >= tp_p) or (signal == 'SELL' and low <= tp_p):
                        exit_price, reason, close_t = float(tp_p), "TP Hit", str(check_bar['time'])
                        exit_found = True
                            
                    if exit_found:
                        pnl_pts = (exit_price - entry_price) if signal == 'BUY' else (entry_price - exit_price)
                        pnl_money = float(round(pnl_pts * HARDCODED_LOT_SIZE * CONTRACT_SIZE, 2))
                        
                        trades.append([
                            int(batch_id), str(strat_name), str(pair), str(signal), open_time,
                            round(entry_price, 5), round(float(sl_p), 5), sl_money,
                            float(HARDCODED_LOT_SIZE), spread, tp_money, round(float(tp_p), 5),
                            round(exit_price, 5), close_t, pnl_money, str(reason)
                        ])
                        idx = j
                        break
                
                if not exit_found:
                    last_bar = df.iloc[-1]
                    last_price = float(last_bar['close'])
                    pnl_pts = (last_price - entry_price) if signal == 'BUY' else (entry_price - last_price)
                    trades.append([
                        int(batch_id), str(strat_name), str(pair), str(signal), open_time,
                        round(entry_price, 5), round(float(sl_p), 5), sl_money,
                        float(HARDCODED_LOT_SIZE), spread, tp_money, round(float(tp_p), 5),
                        round(last_price, 5), str(last_bar['time']), 
                        float(round(pnl_pts * HARDCODED_LOT_SIZE * CONTRACT_SIZE, 2)), "Data Ended"
                    ])
                    break
            
            idx += 1
            if idx % 20 == 0:
                progress_bar.progress(min((idx - warmup) / (total_bars - warmup), 1.0))

        if trades:
            self.cloud.log_batch_results(batch_id, trades)
            return f"✅ {pair}: {len(trades)} trades logged."
        
        return f"😴 {pair}: No confluence found."

    def finalize_show(self, batch_id):
        self.cloud.finalize_batch_stats(batch_id)

    def shutdown(self):
        self.broker.disconnect()