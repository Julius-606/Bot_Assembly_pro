#============================================================================
#---------------------------THE TREND RUNNER (M15)---------------------------
#============================================================================
# "Real Talk" Edition: High Probability, Trend Following, ATR Risk Mgmt.

import pandas as pd
import numpy as np

class Strategy:
    """
    The Mastermind. 🧠
    Encapsulates logic for Trend Following.
    """
    def __init__(self):
        self.name = "Trend Runner v1"

    # ==============================================================================
    # 🧠 INDICATORS
    # ==============================================================================
    def calc_indicators(self, df, params):
        if df.empty: return df
        
        # 1. THE TREND FILTER (200 EMA)
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # 2. VOLATILITY (ATR)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=14).mean()
        
        # 3. MOMENTUM (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().replace(0, 1e-10)
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs)).fillna(50)

        return df

    # ==============================================================================
    # ⚔️ STRATEGY LOGIC
    # ==============================================================================
    def check_trend_runner(self, pair, df, params):
        if len(df) < 200: return None, None, None, None
        
        curr = df.iloc[-1]
        atr = curr['atr'] if curr['atr'] > 0 else 0.0010
        recent_high = df['high'].iloc[-21:-1].max()
        recent_low = df['low'].iloc[-21:-1].min()
        
        # --- LONG SETUP (BUY) ---
        if (curr['close'] > curr['ema_200']) and \
           (curr['close'] > recent_high) and \
           (curr['rsi'] < 70):
               sl = curr['close'] - (atr * 2.0)
               tp = curr['close'] + (atr * 4.0) 
               return 'BUY', sl, tp, 'TREND_RUNNER'

        # --- SHORT SETUP (SELL) ---
        if (curr['close'] < curr['ema_200']) and \
           (curr['close'] < recent_low) and \
           (curr['rsi'] > 30):
               sl = curr['close'] + (atr * 2.0)
               tp = curr['close'] - (atr * 4.0)
               return 'SELL', sl, tp, 'TREND_RUNNER'

        return None, None, None, None

    # ==============================================================================
    # 🚦 EXECUTION
    # ==============================================================================
    def analyze(self, pair, broker, cloud):
        params = cloud.state.get('strategy_params', {})
        df_m15 = broker.fetch_candles(pair, '15m', 300)
        if df_m15.empty: return None, None, None, None
        df_m15 = self.calc_indicators(df_m15, params)
        return self.check_trend_runner(pair, df_m15, params)
