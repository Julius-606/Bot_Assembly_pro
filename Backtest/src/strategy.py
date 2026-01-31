# ==============================================================================
# ---- AI STRATEGY ENGINE v3.0 (Universal Backtester Edition) ----
# ==============================================================================
import pandas as pd
import ta 
import numpy as np
from datetime import datetime

STRATEGY_STATE = {
    "VERSION": "3.0",
    "PARAMS": {
        "EMA_FAST": 10, "EMA_SLOW": 21, "RSI_PERIOD": 14, "RSI_LIMIT_LOW": 30, "RSI_LIMIT_HIGH": 70,
        "ATR_PERIOD": 14, "ATR_MULTIPLIER": 3.0, "RISK_REWARD": 2.0, "ADX_THRESHOLD": 25,
        "DONCHIAN_PERIOD": 20, "KELTNER_MULT": 2.0, "SMA_PERIOD": 200, "STOCH_K": 14, "STOCH_D": 3
    },
    "ACTIVE_CONCOCTION": []
}

class Strategy:
    def __init__(self):
        self.state = STRATEGY_STATE
        self.name = "Custom_Concoction"

    def update_concoction(self, recipe):
        self.state["ACTIVE_CONCOCTION"] = recipe
        self.name = "+".join(recipe) if recipe else "Pure_Price"

    def calc_indicators(self, df):
        if df.empty: return df
        p = self.state["PARAMS"]
        recipe = self.state["ACTIVE_CONCOCTION"]
        
        df = df.copy()
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        # Base ATR for SL/TP
        df['ATR'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=p['ATR_PERIOD']).average_true_range()

        # Dynamic Ingredient Loading
        if "EMA" in recipe:
            df['EMA_F'] = ta.trend.EMAIndicator(df['close'], window=p['EMA_FAST']).ema_indicator()
            df['EMA_S'] = ta.trend.EMAIndicator(df['close'], window=p['EMA_SLOW']).ema_indicator()
        if "RSI" in recipe:
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=p['RSI_PERIOD']).rsi()
        if "MACD" in recipe:
            macd = ta.trend.MACD(df['close'])
            df['MACD_L'] = macd.macd()
            df['MACD_S'] = macd.macd_signal()
        if "Bol" in recipe:
            bb = ta.volatility.BollingerBands(df['close'])
            df['BBU'] = bb.bollinger_hband()
            df['BBL'] = bb.bollinger_lband()
        if "ADX" in recipe:
            df['ADX'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
        if "SMA" in recipe:
            df['SMA'] = ta.trend.SMAIndicator(df['close'], window=p['SMA_PERIOD']).sma_indicator()
        if "Stoch" in recipe:
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=p['STOCH_K'], smooth_window=p['STOCH_D'])
            df['STOCH_K'] = stoch.stoch()
            df['STOCH_D'] = stoch.stoch_signal()
            
        return df

    def analyze_backtest(self, df):
        df = self.calc_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        p = self.state["PARAMS"]
        recipe = self.state["ACTIVE_CONCOCTION"]
        
        buy_vote = True if recipe else False
        sell_vote = True if recipe else False
        
        # --- VOTING LOGIC ---
        if "EMA" in recipe:
            if not (curr['EMA_F'] > curr['EMA_S']): buy_vote = False
            if not (curr['EMA_F'] < curr['EMA_S']): sell_vote = False
        
        if "RSI" in recipe:
            if curr['RSI'] > p['RSI_LIMIT_HIGH']: buy_vote = False
            if curr['RSI'] < p['RSI_LIMIT_LOW']: sell_vote = False
            
        if "ADX" in recipe:
            if curr['ADX'] < p['ADX_THRESHOLD']: 
                buy_vote = False; sell_vote = False

        if "SMA" in recipe:
            if curr['close'] < curr['SMA']: buy_vote = False
            if curr['close'] > curr['SMA']: sell_vote = False

        # --- FINAL CHECK & EXECUTION ---
        atr = curr['ATR']
        if pd.isna(atr) or (not buy_vote and not sell_vote):
            return None, None, None, None

        dist = atr * p['ATR_MULTIPLIER']
        if buy_vote:
            return 'BUY', curr['close'] - dist, curr['close'] + (dist * p['RISK_REWARD']), self.name
        if sell_vote:
            return 'SELL', curr['close'] + dist, curr['close'] - (dist * p['RISK_REWARD']), self.name

        return None, None, None, None