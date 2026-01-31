import pandas as pd
import ta 
import numpy as np

# ==============================================================================
# ---- DARWIN STRATEGY ENGINE v5.0 (Strictness-Dynamic Edition) ----
# ==============================================================================

STRATEGY_STATE = {
    "VERSION": "5.0",
    # 🧬 DYNAMIC PARAMETER MAPPER
    # Strictness now affects the actual periods and thresholds of the indicators.
    "STRICTNESS_MODES": {
        "Low": {
            "EMA_FAST": 10, "EMA_SLOW": 21, "SMA_PERIOD": 20,
            "RSI_PERIOD": 14, "RSI_LOW": 30, "RSI_HIGH": 70,
            "ADX_THRESHOLD": 20, "ATR_PERIOD": 10, "ATR_MULT": 2.5,
            "RR": 1.5, "DONCHIAN": 10, "STOCH_K": 10, "STOCH_D": 3,
            "CCI_PERIOD": 14, "MFI_PERIOD": 10, "ROC_PERIOD": 9, "TRIX_PERIOD": 10,
            "WILLR_PERIOD": 10, "KELTNER_MULT": 1.5, "MACD_F": 12, "MACD_S": 26, "MACD_SIG": 9
        },
        "Medium": {
            "EMA_FAST": 20, "EMA_SLOW": 50, "SMA_PERIOD": 100,
            "RSI_PERIOD": 14, "RSI_LOW": 25, "RSI_HIGH": 75,
            "ADX_THRESHOLD": 30, "ATR_PERIOD": 14, "ATR_MULT": 3.0,
            "RR": 2.0, "DONCHIAN": 20, "STOCH_K": 14, "STOCH_D": 3,
            "CCI_PERIOD": 20, "MFI_PERIOD": 14, "ROC_PERIOD": 12, "TRIX_PERIOD": 15,
            "WILLR_PERIOD": 14, "KELTNER_MULT": 2.0, "MACD_F": 24, "MACD_S": 52, "MACD_SIG": 18
        },
        "High": {
            "EMA_FAST": 50, "EMA_SLOW": 200, "SMA_PERIOD": 200,
            "RSI_PERIOD": 21, "RSI_LOW": 20, "RSI_HIGH": 80,
            "ADX_THRESHOLD": 40, "ATR_PERIOD": 20, "ATR_MULT": 4.0,
            "RR": 3.0, "DONCHIAN": 40, "STOCH_K": 21, "STOCH_D": 5,
            "CCI_PERIOD": 40, "MFI_PERIOD": 21, "ROC_PERIOD": 20, "TRIX_PERIOD": 30,
            "WILLR_PERIOD": 20, "KELTNER_MULT": 3.0, "MACD_F": 48, "MACD_S": 104, "MACD_SIG": 36
        }
    }
}

class Strategy:
    """The Brain 🧠. Dynamic parameters based on user strictness level."""
    def __init__(self):
        self.state = STRATEGY_STATE
        self.name = "Custom_Concoction"

    def update_name(self):
        self.name = "+".join(self.state.get('ACTIVE_CONCOCTION', ["EmptyRecipe"]))

    def calc_indicators(self, df, strictness):
        """Standardizes all 17 indicators using strictness-based params."""
        # Grab the specific param set for this strictness level
        p = self.state["STRICTNESS_MODES"].get(strictness, self.state["STRICTNESS_MODES"]["Medium"])
        recipe = self.state.get("ACTIVE_CONCOCTION", [])
        df = df.copy()
        
        # 🛡️ Foundation: ATR for SL/TP math
        df['ATR'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], p['ATR_PERIOD']).average_true_range()

        # 🌪️ THE BLENDER (No logic left behind)
        if "EMA" in recipe:
            df['EMA_F'] = ta.trend.EMAIndicator(df['close'], p['EMA_FAST']).ema_indicator()
            df['EMA_S'] = ta.trend.EMAIndicator(df['close'], p['EMA_SLOW']).ema_indicator()
        if "SMA" in recipe:
            df['SMA'] = ta.trend.SMAIndicator(df['close'], p['SMA_PERIOD']).sma_indicator()
        if "RSI" in recipe:
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], p['RSI_PERIOD']).rsi()
        if "MACD" in recipe:
            m = ta.trend.MACD(df['close'], window_fast=p['MACD_F'], window_slow=p['MACD_S'], window_sign=p['MACD_SIG'])
            df['MACD'], df['MACD_S'] = m.macd(), m.macd_signal()
        if "Bol" in recipe:
            bb = ta.volatility.BollingerBands(df['close'], window=p['SMA_PERIOD']) # Use SMA period for consistency
            df['BBU'], df['BBL'] = bb.bollinger_hband(), bb.bollinger_lband()
        if "ADX" in recipe:
            df['ADX'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=p['RSI_PERIOD']).adx()
        if "SAR" in recipe:
            df['SAR'] = ta.trend.PSARIndicator(df['high'], df['low'], df['close']).psar()
        if "Ichi" in recipe:
            ichi = ta.trend.IchimokuIndicator(df['high'], df['low'])
            df['ISA'], df['ISB'] = ichi.ichimoku_a(), ichi.ichimoku_b()
        if "Donch" in recipe:
            dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'], p['DONCHIAN'])
            df['DCU'], df['DCL'] = dc.donchian_channel_hband(), dc.donchian_channel_lband()
        if "Stoch" in recipe:
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], p['STOCH_K'], p['STOCH_D'])
            df['STOK'] = stoch.stoch()
        if "CCI" in recipe:
            df['CCI'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], p['CCI_PERIOD']).cci()
        if "MFI" in recipe:
            df['MFI'] = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume'], p['MFI_PERIOD']).money_flow_index()
        if "WillR" in recipe:
            df['WILLR'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'], p['WILLR_PERIOD']).williams_r()
        if "ROC" in recipe:
            df['ROC'] = ta.momentum.ROCIndicator(df['close'], p['ROC_PERIOD']).roc()
        if "TRIX" in recipe:
            df['TRIX'] = ta.trend.TRIXIndicator(df['close'], p['TRIX_PERIOD']).trix()
        if "Kelt" in recipe:
            kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'], window=p['RSI_PERIOD'])
            df['KCU'], df['KCL'] = kc.keltner_channel_hband(), kc.keltner_channel_lband()
            
        return df

    def analyze_backtest(self, df, strictness):
        """Confluence voting with dynamic strictness thresholds."""
        if df.empty or len(df) < 5: return None, None, None, None
        
        # Pass strictness down to calc_indicators so periods shift
        df = self.calc_indicators(df, strictness)
        c, prev = df.iloc[-1], df.iloc[-2]
        
        p = self.state["STRICTNESS_MODES"].get(strictness, self.state["STRICTNESS_MODES"]["Medium"])
        recipe = self.state.get("ACTIVE_CONCOCTION", [])
        
        buy_v, sell_v = 0, 0
        total = len(recipe)
        if total == 0: return None, None, None, None

        # 🗳️ VOTING BOOTH
        if "EMA" in recipe:
            if c['EMA_F'] > c['EMA_S']: buy_v += 1
            if c['EMA_F'] < c['EMA_S']: sell_v += 1
        if "SMA" in recipe:
            if c['close'] > c['SMA']: buy_v += 1
            if c['close'] < c['SMA']: sell_v += 1
        if "RSI" in recipe:
            if c['RSI'] < p['RSI_LOW']: buy_v += 1
            if c['RSI'] > p['RSI_HIGH']: sell_v += 1
        if "MACD" in recipe:
            if c['MACD'] > c['MACD_S']: buy_v += 1
            if c['MACD'] < c['MACD_S']: sell_v += 1
        if "Bol" in recipe:
            if c['close'] > c['BBU']: buy_v += 1
            if c['close'] < c['BBL']: sell_v += 1
        if "ADX" in recipe:
            if c['ADX'] > p['ADX_THRESHOLD']: buy_v += 1; sell_v += 1
        if "SAR" in recipe:
            if c['SAR'] < c['close']: buy_v += 1
            if c['SAR'] > c['close']: sell_v += 1
        if "Ichi" in recipe:
            if c['close'] > c['ISA'] and c['close'] > c['ISB']: buy_v += 1
            if c['close'] < c['ISA'] and c['close'] < c['ISB']: sell_v += 1
        if "Donch" in recipe:
            if c['close'] > prev['DCU']: buy_v += 1
            if c['close'] < prev['DCL']: sell_v += 1
        if "Stoch" in recipe:
            if c['STOK'] < 20: buy_v += 1
            if c['STOK'] > 80: sell_v += 1
        if "CCI" in recipe:
            if c['CCI'] < -100: buy_v += 1
            if c['CCI'] > 100: sell_v += 1
        if "MFI" in recipe:
            if c['MFI'] < 20: buy_v += 1
            if c['MFI'] > 80: sell_v += 1
        if "WillR" in recipe:
            if c['WILLR'] < -80: buy_v += 1
            if c['WILLR'] > -20: sell_v += 1
        if "ROC" in recipe:
            if c['ROC'] > 0: buy_v += 1
            if c['ROC'] < 0: sell_v += 1
        if "TRIX" in recipe:
            if c['TRIX'] > 0: buy_v += 1
            if c['TRIX'] < 0: sell_v += 1
        if "Kelt" in recipe:
            if c['close'] > c['KCU']: buy_v += 1
            if c['close'] < c['KCL']: sell_v += 1

        # ⚖️ CONFLUENCE THRESHOLD (Combined with dynamic params)
        # Low: 40% ingredients | Medium: 70% | High: 90%
        confluence_thresh = {"Low": 0.4, "Medium": 0.7, "High": 0.9}[strictness]
        buy_ok = (buy_v >= total * confluence_thresh)
        sell_ok = (sell_v >= total * confluence_thresh)

        # 💰 EXECUTION
        atr = c['ATR']
        if pd.isna(atr) or (not buy_ok and not sell_ok): return None, None, None, None

        dist = atr * p['ATR_MULT']
        # Immediate float conversion for serialization safety
        if buy_ok: 
            return 'BUY', float(c['close'] - dist), float(c['close'] + (dist * p['RR'])), self.name
        if sell_ok: 
            return 'SELL', float(c['close'] + dist), float(c['close'] - (dist * p['RR'])), self.name
        
        return None, None, None, None