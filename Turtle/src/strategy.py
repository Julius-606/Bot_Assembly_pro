# ==============================================================================
# ---- Turtle Strat ----
# ==============================================================================
# The Legend Returns. Donchian Channel Breakouts. 🐢

import pandas as pd
import numpy as np

class Strategy:
    """
    The Turtle. 🐢
    "Trade what you see, not what you think."
    """
    def __init__(self):
        self.name = "Turtle System 1 (Modified)"

    # ==============================================================================
    # 🧠 INDICATORS
    # ==============================================================================
    def calc_indicators(self, df, params):
        if df.empty: return df
        
        donchian_p = params.get('donchian_period', 20)
        ema_p = params.get('ema_filter', 50)
        atr_p = params.get('atr_period', 20)
        
        # 1. DONCHIAN CHANNELS (The Shell)
        # We need the max High of the LAST 20 candles (excluding current)
        df['donchian_high'] = df['high'].rolling(window=donchian_p).max().shift(1)
        df['donchian_low'] = df['low'].rolling(window=donchian_p).min().shift(1)
        
        # 2. REGIME FILTER (EMA 50) - Optional but recommended for M15
        df['ema_filter'] = df['close'].ewm(span=ema_p, adjust=False).mean()
        
        # 3. VOLATILITY (ATR - N)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=atr_p).mean()
        
        return df

    # ==============================================================================
    # 🚦 EXECUTION
    # ==============================================================================
    def analyze(self, pair, broker, cloud):
        params = cloud.state.get('strategy_params', {})
        
        # Turtle likes M15 or H1. Let's stick to M15 to match the Runner.
        df = broker.get_data(pair, timeframe=15, n=200) 
        
        if df is None: return None, None, None, None

        # Calculate indicators
        df = self.calc_indicators(df, params)
        curr = df.iloc[-1]
        atr = curr['atr']
        
        # --- TURTLE LONG (BUY) ---
        # 1. Price breaks ABOVE the 20-period High
        # 2. Price is ABOVE EMA 50 (Trend is Up)
        if (curr['close'] > curr['donchian_high']) and \
           (curr['close'] > curr['ema_filter']):
               
               # Turtle Logic: SL = 2 * N (ATR)
               sl = curr['close'] - (atr * 2.0)
               # Modified: TP is extended (4N) or trailing
               tp = curr['close'] + (atr * 4.0) 
               
               return 'BUY', sl, tp, 'TURTLE_BREAKOUT'

        # --- TURTLE SHORT (SELL) ---
        # 1. Price breaks BELOW the 20-period Low
        # 2. Price is BELOW EMA 50 (Trend is Down)
        if (curr['close'] < curr['donchian_low']) and \
           (curr['close'] < curr['ema_filter']):
               
               sl = curr['close'] + (atr * 2.0)
               tp = curr['close'] - (atr * 4.0)
               
               return 'SELL', sl, tp, 'TURTLE_BREAKOUT'

        return None, None, None, None