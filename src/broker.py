import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class BrokerAPI:
    def __init__(self):
        self.connected = True

    def _map_symbol(self, pair):
        """Maps our pair format (BTC/USD) to Yahoo format (BTC-USD)."""
        if 'USD' in pair and ('BTC' in pair or 'ETH' in pair or 'SOL' in pair or 'XRP' in pair):
            return f"{pair.replace('/', '-')}" # BTC-USD
        elif '/' in pair:
            return f"{pair.replace('/', '')}=X" # EURUSD=X
        return pair

    def get_symbol_info(self, pair):
        class SymbolInfo:
            def __init__(self, p):
                self.point = 0.01 if 'BTC' in p or 'ETH' in p else 0.0001
                self.spread = 50 if 'BTC' in p else 2 
        return SymbolInfo(pair)

    def get_tick(self, pair):
        symbol = self._map_symbol(pair)
        try:
            ticker = yf.Ticker(symbol)
            # Fast fetch of recent data
            df = ticker.history(period="1d", interval="1m")
            if not df.empty:
                last_price = df['Close'].iloc[-1]
                # Simulating spread since YF gives mid-price mostly
                spread = 0.0002 if 'X' in symbol else 1.0 
                return type('Tick', (object,), {'bid': last_price, 'ask': last_price + spread})
            return None
        except:
            return None

    def fetch_candles(self, pair, timeframe, count):
        # Map timeframe to YFinance interval
        interval_map = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '1d': '1d'}
        yf_interval = interval_map.get(timeframe, '1h')
        
        # Adjust period based on count/interval to ensure we get enough data
        period = "1d"
        if timeframe == '5m': period = "5d"
        if timeframe == '15m': period = "5d"
        if timeframe == '1m': period = "1d"
        
        symbol = self._map_symbol(pair)
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=yf_interval)
            
            if df.empty: return pd.DataFrame()
            
            # Format columns to match our logic (lowercase)
            df = df.reset_index()
            df = df.rename(columns={
                'Datetime': 'time', 'Date': 'time',
                'Open': 'open', 'High': 'high', 
                'Low': 'low', 'Close': 'close', 'Volume': 'tick_volume'
            })
            
            # YF returns timezone-aware datetimes, ensure compatibility
            df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
            
            return df.tail(count)
            
        except Exception as e:
            print(f"⚠️ Candle Fetch Error ({pair}): {e}")
            return pd.DataFrame(columns=['time','open','high','low','close','tick_volume'])

    def execute_trade(self, pair, signal, volume, sl, tp, comment):
        # Execution remains simulated (Paper Trading)
        # But entry price is REAL now.
        tick = self.get_tick(pair)
        
        if not tick:
            # Fallback if tick fails right at execution
            return None
            
        entry = tick.ask if signal == 'BUY' else tick.bid
        
        # Return a receipt object
        class TradeReceipt:
            def __init__(self, p, t):
                self.price = p
                self.ticket = t
        
        return TradeReceipt(entry, int(time.time()))