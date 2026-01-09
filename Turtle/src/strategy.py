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
        self.name = "Turtle System 1 (Risk Clamped)"

    def calc_indicators(self, df, params):
        if df.empty: return df
        
        donchian_p = params.get('donchian_period', 20)
        ema_p = params.get('ema_filter', 50)
        atr_p = params.get('atr_period', 20)
        
        # 1. DONCHIAN CHANNELS
        df['donchian_high'] = df['high'].rolling(window=donchian_p).max().shift(1)
        df['donchian_low'] = df['low'].rolling(window=donchian_p).min().shift(1)
        
        # 2. REGIME FILTER (EMA 50)
        df['ema_filter'] = df['close'].ewm(span=ema_p, adjust=False).mean()
        
        # 3. VOLATILITY (ATR)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=atr_p).mean()
        
        return df

    def analyze(self, pair, broker, cloud):
        params = cloud.state.get('strategy_params', {})
        
        df = broker.get_data(pair, timeframe=15, n=200) 
        
        if df is None: return None, None, None, None

        # Calculate indicators
        df = self.calc_indicators(df, params)
        curr = df.iloc[-1]
        atr = curr['atr']
        price = curr['close']
        
        # 🛡️ RISK CLAMP: Stop loss cannot exceed 1% of price
        # For Gold @ 2000, max SL distance = $20.
        max_sl_dist = price * 0.01 
        
        # Calculated ATR SL
        raw_sl_dist = atr * 2.0
        
        # Use the smaller of the two (ATR or Max Clamp)
        final_sl_dist = min(raw_sl_dist, max_sl_dist)
        
        # --- TURTLE LONG (BUY) ---
        if (curr['close'] > curr['donchian_high']) and \
           (curr['close'] > curr['ema_filter']):
               
               sl = curr['close'] - final_sl_dist
               tp = curr['close'] + (final_sl_dist * 2.0) # 1:2 RR
               
               return 'BUY', sl, tp, 'TURTLE_BREAKOUT'

        # --- TURTLE SHORT (SELL) ---
        if (curr['close'] < curr['donchian_low']) and \
           (curr['close'] < curr['ema_filter']):
               
               sl = curr['close'] + final_sl_dist
               tp = curr['close'] - (final_sl_dist * 2.0)
               
               return 'SELL', sl, tp, 'TURTLE_BREAKOUT'

        return None, None, None, None