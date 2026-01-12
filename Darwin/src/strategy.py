# ==============================================================================
# ---- AI STRATEGY ENGINE v2.0 (The Pantry) ----
# ==============================================================================

import pandas as pd
import pandas_ta as ta  # <--- 🛠️ THE MISSING GUEST (Fixes 'no attribute ta')
import numpy as np
from datetime import datetime

# ==============================================================================
# 🧠 AI EXCLUSIVE ZONE (Gemini edits this via Coach)
# ==============================================================================
STRATEGY_STATE = {
    "VERSION": "2.0",
    
    # The Menu: A catalog of ALL available tools for Gemini to choose from
    "MENU": [
        "EMA_CROSS",        # Trend: Fast EMA crosses Slow EMA
        "RSI_FILTER",       # Momentum: Only buy if RSI not overbought
        "MACD_CONFIRM",     # Momentum: Signal line confirmation
        "BOLLINGER_SQUEEZE",# Volatility: Trade breakout from low vol
        "ADX_FILTER",       # Trend Strength: Only trade if ADX > 25
        "SAR_REVERSAL",     # Trend: Parabolic SAR flips
        "ICHIMOKU_CLOUD",   # Trend: Price above/below Kumo Cloud
        "KELTNER_CHANNEL",  # Volatility: Breakout from ATR bands
        "DONCHIAN_BREAKOUT",# Trend: Turtle Trading (20-day Highs)
        "STOCH_ENTRY",      # Momentum: Stochastic Cross under 20/ over 80
        "CCI_MOMENTUM",     # Momentum: CCI > 100 or < -100
        "FIB_GOLDEN_ZONE"   # Exotic: Price touching 61.8% retracement
    ],

    # The Active Recipe: What are we cooking today?
    "ACTIVE_CONCOCTION": ["ICHIMOKU_CLOUD", "ADX_FILTER"],

    # The Flavors: Hyperparameters
    "PARAMS": {
        "EMA_FAST": 9, "EMA_SLOW": 21,
        "RSI_PERIOD": 14, "RSI_LIMIT_LOW": 30, "RSI_LIMIT_HIGH": 70,
        "ATR_PERIOD": 14, "ATR_MULTIPLIER": 1.5, "RISK_REWARD": 2.0,
        "ADX_THRESHOLD": 25,
        "DONCHIAN_PERIOD": 20,
        "KELTNER_MULT": 2.0,
        "FIB_LOOKBACK": 100
    },

    "BENCHED_PAIRS": {},
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
        """Calculates ONLY the ingredients needed for the current recipe."""
        if df.empty: return df
        p = self.state["PARAMS"]
        recipe = self.state["ACTIVE_CONCOCTION"]

        # 1. ESSENTIALS (Risk)
        df.ta.atr(length=p['ATR_PERIOD'], append=True)

        # 2. TREND
        if "EMA_CROSS" in recipe:
            df.ta.ema(length=p['EMA_FAST'], append=True)
            df.ta.ema(length=p['EMA_SLOW'], append=True)
        if "SAR_REVERSAL" in recipe:
            df.ta.psar(append=True)
        if "ICHIMOKU_CLOUD" in recipe:
            # Ichimoku returns a DataFrame, we need to append carefully
            ichimoku, _ = df.ta.ichimoku()
            df = pd.concat([df, ichimoku], axis=1)
        if "DONCHIAN_BREAKOUT" in recipe:
            df.ta.donchian(lower_length=p['DONCHIAN_PERIOD'], upper_length=p['DONCHIAN_PERIOD'], append=True)
        if "ADX_FILTER" in recipe:
            df.ta.adx(length=14, append=True)

        # 3. MOMENTUM
        if "RSI_FILTER" in recipe:
            df.ta.rsi(length=p['RSI_PERIOD'], append=True)
        if "MACD_CONFIRM" in recipe:
            df.ta.macd(append=True)
        if "STOCH_ENTRY" in recipe:
            df.ta.stoch(append=True)
        if "CCI_MOMENTUM" in recipe:
            df.ta.cci(append=True)

        # 4. VOLATILITY
        if "BOLLINGER_SQUEEZE" in recipe:
            df.ta.bbands(append=True)
        if "KELTNER_CHANNEL" in recipe:
            df.ta.kc(scalar=p['KELTNER_MULT'], append=True)

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
            # PSAR columns are tricky, usually PSARl (long) and PSARs (short)
            # Simplification: Close > PSAR = Bull
            psar_cols = [c for c in df.columns if 'PSAR' in c]
            if psar_cols:
                psar_val = curr[psar_cols[0]] # Usually combined or just check logic
                if curr['close'] < psar_val: buy_vote = False
                if curr['close'] > psar_val: sell_vote = False

        if "ICHIMOKU_CLOUD" in recipe:
            # Span A (ISA) and Span B (ISB)
            # Default names: ISA_9, ISB_26
            span_a = curr['ISA_9']
            span_b = curr['ISB_26']
            if not (curr['close'] > max(span_a, span_b)): buy_vote = False # Above Cloud
            if not (curr['close'] < min(span_a, span_b)): sell_vote = False # Below Cloud

        if "DONCHIAN_BREAKOUT" in recipe:
            # Buy if broke previous High
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
            # Cross Up from oversold
            if not (k < 20 and k > d): buy_vote = False 
            # Cross Down from overbought
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
            # Custom calc: Lookback High/Low
            lb = p['FIB_LOOKBACK']
            high = df['high'].rolling(lb).max().iloc[-1]
            low = df['low'].rolling(lb).min().iloc[-1]
            diff = high - low
            level_618 = high - (diff * 0.618)
            level_500 = high - (diff * 0.500)
            
            # Buy if in zone
            in_zone = level_618 <= curr['close'] <= level_500
            if not in_zone: buy_vote = False; sell_vote = False 
            # Note: This is a pullback strategy, might conflict with trend breakouts

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