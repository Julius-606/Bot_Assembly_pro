# ==============================================================================
# ---- Turtle Strategy v1.3.0 ----
# ==============================================================================
# The Legend Returns. Donchian Channel Breakouts. 🐢

import pandas as pd
import numpy as np

class Strategy:
    """
    The Turtle. 🐢
    "Trade what you see, not what you think."
    """
    def __init__(self, default_params=None):
        self.name = "Turtle System 1 (Risk Clamped)"
        # Use injected params or fallback to safe defaults
        self.default_params = default_params if default_params else {
            "donchian_period": 20, 
            "ema_filter": 50,      
            "atr_period": 20,
            "risk_per_trade": 0.01
        }

    def calc_indicators(self, df, params):
        if df.empty: return df
        
        p = params if params else self.default_params
        
        # 1. DONCHIAN CHANNELS
        # We need the max High of the LAST 20 candles (excluding current)
        df['donchian_high'] = df['high'].rolling(window=p.get('donchian_period', 20)).max().shift(1)
        df['donchian_low'] = df['low'].rolling(window=p.get('donchian_period', 20)).min().shift(1)
        
        # 2. REGIME FILTER (EMA 50) - Optional but recommended for M15
        df['ema_filter'] = df['close'].ewm(span=p.get('ema_filter', 50), adjust=False).mean()
        
        # 3. VOLATILITY (ATR - N)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=p.get('atr_period', 20)).mean()
        
        return df

    def analyze(self, pair, broker, cloud):
        cloud_params = cloud.state.get('strategy_params', {})
        params = cloud_params if cloud_params else self.default_params
        
        # Turtle likes M15 or H1. Let's stick to M15 to match the Runner.
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
        # 1. Price breaks ABOVE the 20-period High
        # 2. Price is ABOVE EMA 50 (Trend is Up)
        if (curr['close'] > curr['donchian_high']) and \
           (curr['close'] > curr['ema_filter']):
               
               # Turtle Logic: SL = 2 * N (ATR)
               sl = curr['close'] - final_sl_dist
               # Modified: TP is extended (4N) or trailing
               tp = curr['close'] + (final_sl_dist * 2.0) # 1:2 RR
               
               return 'BUY', sl, tp, 'TURTLE_BREAKOUT'

        # --- TURTLE SHORT (SELL) ---
        # 1. Price breaks BELOW the 20-period Low
        # 2. Price is BELOW EMA 50 (Trend is Down)
        if (curr['close'] < curr['donchian_low']) and \
           (curr['close'] < curr['ema_filter']):
               
               sl = curr['close'] + final_sl_dist
               tp = curr['close'] - (final_sl_dist * 2.0)
               
               return 'SELL', sl, tp, 'TURTLE_BREAKOUT'

        return None, None, None, None