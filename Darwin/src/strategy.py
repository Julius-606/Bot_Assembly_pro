# ==============================================================================
# ---- AI STRATEGY ENGINE v2.0 (The Pantry) ----
# ==============================================================================

import pandas as pd
import ta # <--- 🛠️ USING STANDARD 'ta' LIBRARY (No git required)
import numpy as np
from datetime import datetime

# ==============================================================================


# 🧠 AI EXCLUSIVE ZONE (Gemini edits this via Coach)
# The Coach (coach.py) uses Regex to surgically update this block.
# ==============================================================================
STRATEGY_STATE = {
    "VERSION": "2.0",
    "MENU": [
        "EMA_CROSS",
        "RSI_FILTER",
        "MACD_CONFIRM",
        "BOLLINGER_SQUEEZE",
        "ADX_FILTER",
        "SAR_REVERSAL",
        "ICHIMOKU_CLOUD",
        "KELTNER_CHANNEL",
        "DONCHIAN_BREAKOUT",
        "STOCH_ENTRY",
        "CCI_MOMENTUM",
        "FIB_GOLDEN_ZONE"
    ],
    "ACTIVE_CONCOCTION": [
        "ICHIMOKU_CLOUD",
        "ADX_FILTER"
    ],
    "PARAMS": {
        "EMA_FAST": 9,
        "EMA_SLOW": 21,
        "RSI_PERIOD": 14,
        "RSI_LIMIT_LOW": 30,
        "RSI_LIMIT_HIGH": 70,
        "ATR_PERIOD": 14,
        "ATR_MULTIPLIER": 1.5,
        "RISK_REWARD": 2.0,
        "ADX_THRESHOLD": 25,
        "DONCHIAN_PERIOD": 20,
        "KELTNER_MULT": 2.0,
        "FIB_LOOKBACK": 100
    },
    "BENCHED_PAIRS": {
        "AUDUSD": "2026-01-15 21:15:49",
        "GBPUSD": "2026-01-15 21:23:04",
        "EURUSD": "2026-01-15 21:23:04"
    },
    "MODE": "STANDARD"
}
# ==============================================================================
# 🛑 END AI ZONE
# ==============================================================================

class Strategy:
    """
    Darwin v2.0 🧬
    """
    def __init__(self):
        # Dynamic Name based on Active Ingredients
        ingredients = "+".join(STRATEGY_STATE['ACTIVE_CONCOCTION'])
        self.name = f"Darwin v{STRATEGY_STATE['VERSION']} ({ingredients})"
        self.state = STRATEGY_STATE

    def check_bench(self, pair):
        benched_until = self.state["BENCHED_PAIRS"].get(pair)
        if benched_until:
            lift_time = datetime.strptime(benched_until, "%Y-%m-%d %H:%M:%S")
            return datetime.now() < lift_time
        return False

    def calc_indicators(self, df):
        """Calculates ONLY the ingredients needed for the current recipe using 'ta' lib."""
        if df.empty: return df
        p = self.state["PARAMS"]
        recipe = self.state["ACTIVE_CONCOCTION"]
        
        # Ensure numeric types
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        # 1. ESSENTIALS (Risk) - ATR
        # Manually assign to match old naming convention
        atr_obj = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=p['ATR_PERIOD'])
        df[f"ATRr_{p['ATR_PERIOD']}"] = atr_obj.average_true_range()

        # 2. TREND
        if "EMA_CROSS" in recipe:
            df[f"EMA_{p['EMA_FAST']}"] = ta.trend.EMAIndicator(close=df['close'], window=p['EMA_FAST']).ema_indicator()
            df[f"EMA_{p['EMA_SLOW']}"] = ta.trend.EMAIndicator(close=df['close'], window=p['EMA_SLOW']).ema_indicator()
            
        if "SAR_REVERSAL" in recipe:
            # 'ta' gives PSAR values directly
            df['PSAR'] = ta.trend.PSARIndicator(high=df['high'], low=df['low'], close=df['close']).psar()
            
        if "ICHIMOKU_CLOUD" in recipe:
            ichi = ta.trend.IchimokuIndicator(high=df['high'], low=df['low'])
            df['ISA_9'] = ichi.ichimoku_a()
            df['ISB_26'] = ichi.ichimoku_b()
            
        if "DONCHIAN_BREAKOUT" in recipe:
            dc = ta.volatility.DonchianChannel(high=df['high'], low=df['low'], close=df['close'], window=p['DONCHIAN_PERIOD'])
            df[f"DCU_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"] = dc.donchian_channel_hband()
            df[f"DCL_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"] = dc.donchian_channel_lband()
            
        if "ADX_FILTER" in recipe:
            df['ADX_14'] = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()

        # 3. MOMENTUM
        if "RSI_FILTER" in recipe:
            df[f"RSI_{p['RSI_PERIOD']}"] = ta.momentum.RSIIndicator(close=df['close'], window=p['RSI_PERIOD']).rsi()
            
        if "MACD_CONFIRM" in recipe:
            macd = ta.trend.MACD(close=df['close'])
            df['MACD_12_26_9'] = macd.macd() # Standard MACD line
            
        if "STOCH_ENTRY" in recipe:
            stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
            df['STOCHk_14_3_3'] = stoch.stoch()
            df['STOCHd_14_3_3'] = stoch.stoch_signal()
            
        if "CCI_MOMENTUM" in recipe:
            df['CCI_14_0.015'] = ta.trend.CCIIndicator(high=df['high'], low=df['low'], close=df['close']).cci()

        # 4. VOLATILITY
        if "BOLLINGER_SQUEEZE" in recipe:
            bb = ta.volatility.BollingerBands(close=df['close'])
            df['BBU_5_2.0'] = bb.bollinger_hband()
            df['BBL_5_2.0'] = bb.bollinger_lband()
            
        if "KELTNER_CHANNEL" in recipe:
            # Manual Keltner Calculation (EMA +/- ATR * Mult)
            kc_ema = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
            kc_atr = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=10).average_true_range()
            mult = p['KELTNER_MULT']
            df[f"KCUe_20_{mult}"] = kc_ema + (kc_atr * mult)
            df[f"KCLe_20_{mult}"] = kc_ema - (kc_atr * mult)

        return df

    def analyze(self, pair, broker, cloud):
        if self.check_bench(pair): return None, None, None, None

        df = broker.get_data(pair, timeframe=15, n=300)
        if df is None or df.empty: return None, None, None, None
        
        df = self.calc_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        p = self.state["PARAMS"]
        recipe = self.state["ACTIVE_CONCOCTION"]
        
        # VOTING SYSTEM
        buy_vote = True
        sell_vote = True
        
        # --- TREND LOGIC ---
        if "EMA_CROSS" in recipe:
            fast, slow = curr[f"EMA_{p['EMA_FAST']}"], curr[f"EMA_{p['EMA_SLOW']}"]
            if not (fast > slow): buy_vote = False
            if not (fast < slow): sell_vote = False

        if "SAR_REVERSAL" in recipe:
            # Logic: Close > PSAR = Bull
            psar_val = curr['PSAR']
            if curr['close'] < psar_val: buy_vote = False
            if curr['close'] > psar_val: sell_vote = False

        if "ICHIMOKU_CLOUD" in recipe:
            span_a = curr['ISA_9']
            span_b = curr['ISB_26']
            if not (curr['close'] > max(span_a, span_b)): buy_vote = False # Above Cloud
            if not (curr['close'] < min(span_a, span_b)): sell_vote = False # Below Cloud

        if "DONCHIAN_BREAKOUT" in recipe:
            upper = prev[f"DCU_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"]
            lower = prev[f"DCL_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"]
            if not (curr['close'] > upper): buy_vote = False
            if not (curr['close'] < lower): sell_vote = False

        # --- MOMENTUM LOGIC ---
        if "RSI_FILTER" in recipe:
            rsi = curr[f"RSI_{p['RSI_PERIOD']}"]
            if rsi > p['RSI_LIMIT_HIGH']: buy_vote = False
            if rsi < p['RSI_LIMIT_LOW']: sell_vote = False

        if "CCI_MOMENTUM" in recipe:
            cci = curr['CCI_14_0.015']
            if cci < 100: buy_vote = False
            if cci > -100: sell_vote = False

        if "STOCH_ENTRY" in recipe:
            k, d = curr['STOCHk_14_3_3'], curr['STOCHd_14_3_3']
            if not (k < 20 and k > d): buy_vote = False 
            if not (k > 80 and k < d): sell_vote = False

        # --- VOLATILITY LOGIC ---
        if "KELTNER_CHANNEL" in recipe:
            upper = curr[f"KCUe_20_{p['KELTNER_MULT']}"]
            lower = curr[f"KCLe_20_{p['KELTNER_MULT']}"]
            if curr['close'] < upper: buy_vote = False
            if curr['close'] > lower: sell_vote = False

        if "ADX_FILTER" in recipe:
            if curr['ADX_14'] < p['ADX_THRESHOLD']:
                buy_vote = False; sell_vote = False

        # --- EXOTIC LOGIC ---
        if "FIB_GOLDEN_ZONE" in recipe:
            lb = p['FIB_LOOKBACK']
            high = df['high'].rolling(lb).max().iloc[-1]
            low = df['low'].rolling(lb).min().iloc[-1]
            diff = high - low
            level_618 = high - (diff * 0.618)
            level_500 = high - (diff * 0.500)
            
            in_zone = level_618 <= curr['close'] <= level_500
            if not in_zone: buy_vote = False; sell_vote = False 

        # --- EXECUTION ---
        atr = curr[f"ATRr_{p['ATR_PERIOD']}"]
        
        if buy_vote and not sell_vote:
            sl_dist = atr * p['ATR_MULTIPLIER']
            sl = curr['close'] - sl_dist
            tp = curr['close'] + (sl_dist * p['RISK_REWARD'])
            return 'BUY', sl, tp, f"Darwin_{self.state['VERSION']}"

        elif sell_vote and not buy_vote:
            sl_dist = atr * p['ATR_MULTIPLIER']
            sl = curr['close'] + sl_dist
            tp = curr['close'] - (sl_dist * p['RISK_REWARD'])
            return 'SELL', sl, tp, f"Darwin_{self.state['VERSION']}"

        return None, None, None, None