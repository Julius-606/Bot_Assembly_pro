# ==============================================================================
# ---- Trend Runner Strategy v2.4.0 ----
# ==============================================================================
# "Real Talk" Edition: High Probability, Trend Following, ATR Risk Mgmt.

import pandas as pd
import numpy as np

class Strategy:
    """
    The Mastermind. 🧠
    Encapsulates logic for Trend Following.
    """
    def __init__(self, default_params=None):
        self.name = "Trend Runner v1.4 (Risk Clamped)"
        # Use injected params or fallback to safe defaults
        self.default_params = default_params if default_params else {
            "ema_period": 200,
            "rsi_period": 14,
            "atr_period": 14,
            "risk_per_trade": 0.01
        }

    # ==============================================================================
    # 🧠 INDICATORS
    # ==============================================================================
    def calc_indicators(self, df, params):
        if df.empty: return df
        
        p = params if params else self.default_params
        ema_p = p.get('ema_period', 200)
        
        # 1. THE TREND FILTER (EMA)
        df['ema_200'] = df['close'].ewm(span=ema_p, adjust=False).mean()
        
        # 2. VOLATILITY (ATR)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=p.get('atr_period', 14)).mean()
        
        # 3. MOMENTUM (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=p.get('rsi_period', 14)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=p.get('rsi_period', 14)).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df

    # ==============================================================================
    # 🚦 EXECUTION
    # ==============================================================================
    def analyze(self, pair, broker, cloud):
        # Prefer cloud state params, fallback to defaults
        cloud_params = cloud.state.get('strategy_params', {})
        params = cloud_params if cloud_params else self.default_params
        
        # Pulling M15
        df = broker.get_data(pair, timeframe=15, n=200) 
        
        if df is None: return None, None, None, None

        # Calculate indicators
        df = self.calc_indicators(df, params)
        curr = df.iloc[-1]
        atr = curr['atr']
        price = curr['close']
        
        # Recent High/Low structure (5 candle lookback)
        recent_high = df['high'].iloc[-6:-1].max()
        recent_low = df['low'].iloc[-6:-1].min()
        
        # 🛡️ RISK CLAMP: SL cannot exceed 1% of price
        max_sl_dist = price * 0.01 
        raw_sl_dist = atr * 2.0
        final_sl_dist = min(raw_sl_dist, max_sl_dist)
        
        # --- LONG SETUP (BUY) ---
        if (curr['close'] > curr['ema_200']) and \
           (curr['close'] > recent_high) and \
           (curr['rsi'] < 85): 
               sl = curr['close'] - final_sl_dist
               tp = curr['close'] + (final_sl_dist * 2.0) # 1:2 RR
               return 'BUY', sl, tp, 'TREND_RUNNER'

        # --- SHORT SETUP (SELL) ---
        if (curr['close'] < curr['ema_200']) and \
           (curr['close'] < recent_low) and \
           (curr['rsi'] > 15): 
               sl = curr['close'] + final_sl_dist
               tp = curr['close'] - (final_sl_dist * 2.0)
               return 'SELL', sl, tp, 'TREND_RUNNER'

        return None, None, None, None