import MetaTrader5 as mt5
import pandas as pd
from config import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

class BrokerAPI:
    """The Middleman 👔. Fetches real OHLC from the backtest terminal."""
    def __init__(self):
        self.connected = False
        self.tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }

    def startup(self):
        # Using the specific MT5_PATH from config.py
        if not mt5.initialize(path=MT5_PATH):
            return False, f"MT5 Init Failed: {mt5.last_error()}"
        
        if not mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
            return False, f"MT5 Login Failed: {mt5.last_error()}"
        
        self.connected = True
        return True, "✅ MT5 Grid Connected"

    def get_historical_data(self, symbol, tf_str, start_dt, end_dt):
        if not self.connected: return None
        tf = self.tf_map.get(tf_str, mt5.TIMEFRAME_M15)
        
        rates = mt5.copy_rates_range(symbol, tf, start_dt, end_dt)
        if rates is None or len(rates) == 0:
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def disconnect(self):
        mt5.shutdown()