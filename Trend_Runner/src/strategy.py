# ==============================================================================
# ---- Trend Runner Strat ----
# ==============================================================================
# "Real Talk" Edition: High Probability, Trend Following, ATR Risk Mgmt.

import pandas as pd
import numpy as np

class Strategy:
    """
    The Mastermind. 🧠
    Encapsulates logic for Trend Following.
    """
    def __init__(self):
        self.name = "Trend Runner v1.3 (Agile)"

    # ==============================================================================
    # 🧠 INDICATORS
    # ==============================================================================
    def calc_indicators(self, df, params):
        if df.empty: return df
        
        ema_p = params.get('ema_period', 200) 
        
        # 1. THE TREND FILTER (EMA)
        df['ema_200'] = df['close'].ewm(span=ema_p, adjust=False).mean()
        
        # 2. VOLATILITY (ATR)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=params.get('atr_period', 14)).mean()
        
        # 3. MOMENTUM (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params.get('rsi_period', 14)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params.get('rsi_period', 14)).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df

    # ==============================================================================
    # 🚦 EXECUTION
    # ==============================================================================
    def analyze(self, pair, broker, cloud):
        params = cloud.state.get('strategy_params', {})
        
        # Pulling M15
        df = broker.get_data(pair, timeframe=15, n=200) 
        
        if df is None: return None, None, None, None

        # Calculate indicators
        df = self.calc_indicators(df, params)
        curr = df.iloc[-1]
        atr = curr['atr']
        
        # Recent High/Low structure
        # 🛠️ TUNING: Reduced lookback from 8 to 5 candles for faster entries
        recent_high = df['high'].iloc[-6:-1].max()
        recent_low = df['low'].iloc[-6:-1].min()
        
        # --- LONG SETUP (BUY) ---
        if (curr['close'] > curr['ema_200']) and \
           (curr['close'] > recent_high) and \
           (curr['rsi'] < 85): # Relaxed RSI cap
               sl = curr['close'] - (atr * 2.0)
               tp = curr['close'] + (atr * 4.0) 
               return 'BUY', sl, tp, 'TREND_RUNNER'

        # --- SHORT SETUP (SELL) ---
        if (curr['close'] < curr['ema_200']) and \
           (curr['close'] < recent_low) and \
           (curr['rsi'] > 15): # Relaxed RSI floor
               sl = curr['close'] + (atr * 2.0)
               tp = curr['close'] - (atr * 4.0)
               return 'SELL', sl, tp, 'TREND_RUNNER'

        return None, None, None, None