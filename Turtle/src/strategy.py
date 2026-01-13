# ==============================================================================
# ---- Turtle Strategy v1.4.0 (Risk Guarded) ----
# ==============================================================================
# The Legend Returns. Donchian Channel Breakouts. 🐢

import pandas as pd
import numpy as np
import MetaTrader5 as mt5 # Needed for tick value lookups
from config import FIXED_LOT_SIZE # Needed for monetary risk calc

class Strategy:
    """
    The Turtle. 🐢
    "Trade what you see, not what you think."
    """
    def __init__(self, default_params=None):
        self.name = "Turtle System 1 (3% Hard Clamp)"
        # Use injected params or fallback to safe defaults
        self.default_params = default_params if default_params else {
            "donchian_period": 20, 
            "ema_filter": 50,      
            "atr_period": 20,
            "risk_per_trade": 0.01,
            "max_risk_pct": 0.03
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
        
        # 1. Base ATR SL Distance
        raw_sl_dist = atr * 2.0
        
        # 2. 🛡️ 3% MONETARY RISK CLAMP (The "Anti-Rekt" Shield)
        balance = cloud.state.get('current_balance', 0)
        max_risk_pct = params.get('max_risk_pct', 0.03) # Default 3%
        
        final_sl_dist = raw_sl_dist
        clamp_msg = None # 🤫 Silence unless triggered

        if balance > 0:
            # Max dollar amount we can lose (e.g., $100 * 0.03 = $3.00)
            max_loss_usd = balance * max_risk_pct
            
            # Get Symbol Metrics to convert Price Distance -> Dollars
            sym_info = mt5.symbol_info(pair)
            if sym_info:
                tick_value = sym_info.trade_tick_value # Value of 1 tick for 1 lot (e.g. $1 for EURUSD, $0.10 for Gold sometimes)
                tick_size = sym_info.trade_tick_size   # Size of 1 tick (e.g. 0.00001 or 0.01)
                
                # Check for zero division
                if tick_size > 0 and tick_value > 0:
                    # Calculate how much $$$ a 1.00 price move is worth for our FIXED_LOT_SIZE
                    # Formula: (TickValue / TickSize) * Volume
                    value_per_price_unit = (tick_value / tick_size) * FIXED_LOT_SIZE
                    
                    if value_per_price_unit > 0:
                        # Max Price Distance = Max $$$ / $$$ per unit
                        max_price_dist_allowed = max_loss_usd / value_per_price_unit
                        
                        # Apply Clamp
                        if raw_sl_dist > max_price_dist_allowed:
                            # 🤫 Store the message, don't print it yet!
                            clamp_msg = f"   ⚠️ Risk Clamp: {pair} SL reduced from {raw_sl_dist:.4f} to {max_price_dist_allowed:.4f} (Max -${max_loss_usd:.2f})"
                            final_sl_dist = max_price_dist_allowed

        # --- TURTLE LONG (BUY) ---
        if (curr['close'] > curr['donchian_high']) and \
           (curr['close'] > curr['ema_filter']):
               
               if clamp_msg: print(clamp_msg) # 🗣️ NOW we scream because we are trading
               
               sl = curr['close'] - final_sl_dist
               # TP is still based on the *original* idea or the clamped one? 
               # Safe bet: Use clamped distance for RR, or keep original target? 
               # Let's keep TP at 2x the ACTUAL risk taken to maintain 1:2 RR.
               tp = curr['close'] + (final_sl_dist * 2.0)
               
               return 'BUY', sl, tp, 'TURTLE_BREAKOUT'

        # --- TURTLE SHORT (SELL) ---
        if (curr['close'] < curr['donchian_low']) and \
           (curr['close'] < curr['ema_filter']):
               
               if clamp_msg: print(clamp_msg) # 🗣️ NOW we scream because we are trading
               
               sl = curr['close'] + final_sl_dist
               tp = curr['close'] - (final_sl_dist * 2.0)
               
               return 'SELL', sl, tp, 'TURTLE_BREAKOUT'

        return None, None, None, None