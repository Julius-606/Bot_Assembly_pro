# ==============================================================================
# ---- Trend Runner Strategy v2.5.0 ----
# ==============================================================================
# "Ironclad" Edition: Hard Risk Clamping implemented.

import pandas as pd
import numpy as np
import MetaTrader5 as mt5 # Imported for symbol info access
from config import FIXED_LOT_SIZE, MAX_RISK_PER_TRADE_PCT

class Strategy:
    """
    The Mastermind. 🧠
    Encapsulates logic for Trend Following with strict % equity risk rules.
    """
    def __init__(self, default_params=None):
        self.name = "Trend Runner v2.5 (3% Limit)"
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
        
        # ---------------------------------------------------------
        # 🛡️ STRICT RISK CLAMP (3% RULE)
        # ---------------------------------------------------------
        # Get Account Balance
        balance = cloud.state.get('current_balance', 0)
        if balance <= 0: balance = 100 # Fallback safety for division
        
        # Calculate Max Dollar Loss allowed
        max_loss_usd = balance * MAX_RISK_PER_TRADE_PCT
        
        # Get Contract Size (e.g. 100 for XAU, 100000 for EUR)
        sym_info = mt5.symbol_info(pair)
        contract_size = sym_info.trade_contract_size if sym_info else 100000
        
        # Calculate Logic SL Distance (ATR Based)
        # Standard: 2 * ATR
        raw_sl_dist = atr * 2.0
        
        # Calculate the Dollar cost of that SL distance
        # Loss = Volume * Contract_Size * Price_Diff
        potential_loss_usd = FIXED_LOT_SIZE * contract_size * raw_sl_dist
        
        final_sl_dist = raw_sl_dist
        
        # IF potential loss > 3% allowed, Force Clamp
        if potential_loss_usd > max_loss_usd:
            # Force the distance to match exactly 3%
            # Price_Diff = Max_Loss / (Volume * Contract_Size)
            forced_dist = max_loss_usd / (FIXED_LOT_SIZE * contract_size)
            final_sl_dist = forced_dist
            # print(f"   🛡️ RISK ALERT {pair}: SL clamped from {raw_sl_dist:.4f} to {forced_dist:.4f} (${max_loss_usd:.2f} max)")
            
        # ---------------------------------------------------------

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