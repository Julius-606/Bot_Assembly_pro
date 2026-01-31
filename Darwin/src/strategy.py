# ==============================================================================
# ---- AI STRATEGY ENGINE v2.3 (Lite Edition) ----
# ==============================================================================

import pandas as pd
import ta 
import numpy as np
import importlib
import sys
from datetime import datetime

# ==============================================================================



















































# 🧠 AI EXCLUSIVE ZONE (Gemini edits this via Coach)
# The Coach (coach.py) uses Regex to surgically update this block.
# ==============================================================================
STRATEGY_STATE = {
    "VERSION": "3.4",
    "MENU": [
        "EMA",
        "RSI",
        "MACD",
        "Bol",
        "ADX",
        "SAR",
        "Ichi",
        "Kelt",
        "Donch",
        "Stoch",
        "CCI",
        "Fib",
        "SMA",
        "WillR",
        "MFI",
        "ROC",
        "TRIX"
    ],
    "ACTIVE_CONCOCTION": [
        "Donch",
        "WillR",
        "ADX"
    ],
    "PARAMS": {
        "EMA_FAST": 20,
        "EMA_SLOW": 80,
        "RSI_PERIOD": 14,
        "RSI_LIMIT_LOW": 30,
        "RSI_LIMIT_HIGH": 70,
        "ATR_PERIOD": 20,
        "ATR_MULTIPLIER": 3.0,
        "RISK_REWARD": 2.0,
        "ADX_THRESHOLD": 30,
        "DONCHIAN_PERIOD": 40,
        "KELTNER_MULT": 2.0,
        "FIB_LOOKBACK": 100,
        "SMA_PERIOD": 50,
        "WILLIAMS_PERIOD": 14,
        "MFI_PERIOD": 14,
        "ROC_PERIOD": 12,
        "TRIX_PERIOD": 15
    },
    "BENCHED_PAIRS": {
        "NZDJPY": "2026-01-30 19:56:11",
        "GBPAUD": "2026-01-30 19:56:11",
        "EURCAD": "2026-01-30 19:56:11",
        "EURJPY": "2026-01-30 19:56:11",
        "CHFJPY": "2026-01-30 19:56:11"
    },
    "MODE": "STANDARD"
}
# ==============================================================================
# 🛑 END AI ZONE
# ==============================================================================

class Strategy:
    """
    Darwin v2.1 🧬
    """
    def __init__(self):
        # Initial Load
        self.state = STRATEGY_STATE
        self.update_name()

    def update_name(self):
        # 📝 CHANGE: Removed "Darwin v3.1" prefix. Now it's just the ingredients joined by '+'.
        # Example: "EMA+MACD+Bol" (12 chars) -> Fits easily in MT5.
        self.name = "+".join(self.state['ACTIVE_CONCOCTION'])

    def refresh_state(self):
        """
        🛠️ HINDENBURG FIX:
        Reloads the module itself to pick up changes made by the Coach
        to the STRATEGY_STATE dict on disk.
        """
        try:
            # 1. Reload the current module
            importlib.reload(sys.modules[__name__])
            
            # 2. Update the instance's reference to the new variable
            # We access the module from sys.modules to get the fresh object
            new_state = sys.modules[__name__].STRATEGY_STATE
            self.state = new_state
            
            # 3. Update Name
            self.update_name()
            # print("   🧬 Strategy State Refreshed (Hot-Reload).")
        except Exception as e:
            print(f"   ⚠️ Strategy Refresh Failed: {e}")

    def check_bench(self, pair):
        benched_until = self.state["BENCHED_PAIRS"].get(pair)
        if benched_until:
            lift_time = datetime.strptime(benched_until, "%Y-%m-%d %H:%M:%S")
            # If now is BEFORE lift time, we are still benched.
            is_benched = datetime.now() < lift_time
            if is_benched:
                # print(f"   🚫 {pair} is warming the bench until {benched_until}")
                pass
            return is_benched
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
        
        # 🛠️ For MFI, we need volume (MT5 gives tick_volume)
        if 'tick_volume' in df.columns:
            volume_col = df['tick_volume']
        else:
            volume_col = df['volume'] if 'volume' in df.columns else None

        # 1. ESSENTIALS (Risk) - ATR
        # Manually assign to match old naming convention
        atr_obj = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=p['ATR_PERIOD'])
        df[f"ATRr_{p['ATR_PERIOD']}"] = atr_obj.average_true_range()

        # 2. TREND
        if "EMA" in recipe:
            df[f"EMA_{p['EMA_FAST']}"] = ta.trend.EMAIndicator(close=df['close'], window=p['EMA_FAST']).ema_indicator()
            df[f"EMA_{p['EMA_SLOW']}"] = ta.trend.EMAIndicator(close=df['close'], window=p['EMA_SLOW']).ema_indicator()
        
        if "SMA" in recipe:
            df[f"SMA_{p['SMA_PERIOD']}"] = ta.trend.SMAIndicator(close=df['close'], window=p['SMA_PERIOD']).sma_indicator()
            
        if "SAR" in recipe:
            # 'ta' gives PSAR values directly
            df['PSAR'] = ta.trend.PSARIndicator(high=df['high'], low=df['low'], close=df['close']).psar()
            
        if "Ichi" in recipe:
            ichi = ta.trend.IchimokuIndicator(high=df['high'], low=df['low'])
            df['ISA_9'] = ichi.ichimoku_a()
            df['ISB_26'] = ichi.ichimoku_b()
            
        if "Donch" in recipe:
            dc = ta.volatility.DonchianChannel(high=df['high'], low=df['low'], close=df['close'], window=p['DONCHIAN_PERIOD'])
            df[f"DCU_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"] = dc.donchian_channel_hband()
            df[f"DCL_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"] = dc.donchian_channel_lband()
            
        if "ADX" in recipe:
            df['ADX_14'] = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()
            
        if "TRIX" in recipe:
            df[f"TRIX_{p['TRIX_PERIOD']}"] = ta.trend.TRIXIndicator(close=df['close'], window=p['TRIX_PERIOD']).trix()

        # 3. MOMENTUM
        if "RSI" in recipe:
            df[f"RSI_{p['RSI_PERIOD']}"] = ta.momentum.RSIIndicator(close=df['close'], window=p['RSI_PERIOD']).rsi()
            
        if "MACD" in recipe:
            macd = ta.trend.MACD(close=df['close'])
            df['MACD_12_26_9'] = macd.macd() # Standard MACD line
            
        if "Stoch" in recipe:
            stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
            df['STOCHk_14_3_3'] = stoch.stoch()
            df['STOCHd_14_3_3'] = stoch.stoch_signal()
            
        if "CCI" in recipe:
            df['CCI_14_0.015'] = ta.trend.CCIIndicator(high=df['high'], low=df['low'], close=df['close']).cci()
            
        if "WillR" in recipe:
            df[f"WILLR_{p['WILLIAMS_PERIOD']}"] = ta.momentum.WilliamsRIndicator(high=df['high'], low=df['low'], close=df['close'], lbp=p['WILLIAMS_PERIOD']).williams_r()
            
        if "ROC" in recipe:
            df[f"ROC_{p['ROC_PERIOD']}"] = ta.momentum.ROCIndicator(close=df['close'], window=p['ROC_PERIOD']).roc()
            
        if "MFI" in recipe and volume_col is not None:
            df[f"MFI_{p['MFI_PERIOD']}"] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=volume_col, window=p['MFI_PERIOD']).money_flow_index()

        # 4. VOLATILITY
        if "Bol" in recipe:
            bb = ta.volatility.BollingerBands(close=df['close'])
            df['BBU_5_2.0'] = bb.bollinger_hband()
            df['BBL_5_2.0'] = bb.bollinger_lband()
            
        if "Kelt" in recipe:
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
        if "EMA" in recipe:
            fast, slow = curr[f"EMA_{p['EMA_FAST']}"], curr[f"EMA_{p['EMA_SLOW']}"]
            if not (fast > slow): buy_vote = False
            if not (fast < slow): sell_vote = False
            
        if "SMA" in recipe:
            # Simple Logic: Price > SMA 200 = Bullish
            sma = curr[f"SMA_{p['SMA_PERIOD']}"]
            if curr['close'] < sma: buy_vote = False
            if curr['close'] > sma: sell_vote = False
            
        if "TRIX" in recipe:
            # TRIX > 0 Bullish, TRIX < 0 Bearish
            trix = curr[f"TRIX_{p['TRIX_PERIOD']}"]
            if trix < 0: buy_vote = False
            if trix > 0: sell_vote = False

        if "SAR" in recipe:
            # Logic: Close > PSAR = Bull
            psar_val = curr['PSAR']
            if curr['close'] < psar_val: buy_vote = False
            if curr['close'] > psar_val: sell_vote = False

        if "Ichi" in recipe:
            span_a = curr['ISA_9']
            span_b = curr['ISB_26']
            if not (curr['close'] > max(span_a, span_b)): buy_vote = False # Above Cloud
            if not (curr['close'] < min(span_a, span_b)): sell_vote = False # Below Cloud

        if "Donch" in recipe:
            upper = prev[f"DCU_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"]
            lower = prev[f"DCL_{p['DONCHIAN_PERIOD']}_{p['DONCHIAN_PERIOD']}"]
            if not (curr['close'] > upper): buy_vote = False
            if not (curr['close'] < lower): sell_vote = False

        # --- MOMENTUM LOGIC ---
        if "RSI" in recipe:
            rsi = curr[f"RSI_{p['RSI_PERIOD']}"]
            if rsi > p['RSI_LIMIT_HIGH']: buy_vote = False
            if rsi < p['RSI_LIMIT_LOW']: sell_vote = False
            
        if "WillR" in recipe:
            # Range is -100 to 0. > -50 is Bullish momentum.
            wr = curr[f"WILLR_{p['WILLIAMS_PERIOD']}"]
            if wr < -50: buy_vote = False
            if wr > -50: sell_vote = False
            
        if "MFI" in recipe and f"MFI_{p['MFI_PERIOD']}" in df.columns:
            mfi = curr[f"MFI_{p['MFI_PERIOD']}"]
            # > 50 Bullish
            if mfi < 50: buy_vote = False
            if mfi > 50: sell_vote = False
            
        if "ROC" in recipe:
            roc = curr[f"ROC_{p['ROC_PERIOD']}"]
            if roc < 0: buy_vote = False
            if roc > 0: sell_vote = False

        if "CCI" in recipe:
            cci = curr['CCI_14_0.015']
            if cci < 100: buy_vote = False
            if cci > -100: sell_vote = False

        if "Stoch" in recipe:
            k, d = curr['STOCHk_14_3_3'], curr['STOCHd_14_3_3']
            if not (k < 20 and k > d): buy_vote = False 
            if not (k > 80 and k < d): sell_vote = False

        # --- VOLATILITY LOGIC ---
        if "Kelt" in recipe:
            upper = curr[f"KCUe_20_{p['KELTNER_MULT']}"]
            lower = curr[f"KCLe_20_{p['KELTNER_MULT']}"]
            if curr['close'] < upper: buy_vote = False
            if curr['close'] > lower: sell_vote = False

        if "ADX" in recipe:
            if curr['ADX_14'] < p['ADX_THRESHOLD']:
                buy_vote = False; sell_vote = False

        # --- EXOTIC LOGIC ---
        if "Fib" in recipe:
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
            return 'BUY', sl, tp, self.name

        elif sell_vote and not buy_vote:
            sl_dist = atr * p['ATR_MULTIPLIER']
            sl = curr['close'] + sl_dist
            tp = curr['close'] - (sl_dist * p['RISK_REWARD'])
            return 'SELL', sl, tp, self.name

        return None, None, None, None