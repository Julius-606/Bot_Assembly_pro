#============================================================================
#---------------------------THE TREND RUNNER (M15)---------------------------
#============================================================================
# "Real Talk" Edition: High Probability, Trend Following, ATR Risk Mgmt.

import pandas as pd
import numpy as np

# ==============================================================================
# 🧠 INDICATORS
# ==============================================================================

def calc_indicators(df, params):
    """
    Calculates the 'Holy Trinity' of Algo Trading:
    1. Trend (EMA 200)
    2. Volatility (ATR)
    3. Momentum (RSI)
    """
    if df.empty: return df
    
    # 1. THE TREND FILTER (200 EMA)
    # The most respected moving average by institutions.
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. VOLATILITY (ATR - Average True Range)
    # Measures how much the price is actually moving.
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['atr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1).rolling(window=14).mean()
    
    # 3. MOMENTUM (RSI)
    # Just to make sure we aren't buying at the absolute top.
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().replace(0, 1e-10)
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs)).fillna(50)

    return df

# ==============================================================================
# ⚔️ STRATEGY LOGIC
# ==============================================================================

def check_trend_runner(pair, df, params):
    """
    The Strategy:
    1. Identify Trend (Above/Below 200 EMA).
    2. Wait for a Breakout of the recent 20-candle High/Low.
    3. Enter with wide stops to let it run.
    """
    # We need at least 200 candles to calculate the EMA 200
    if len(df) < 200: return None, None, None, None
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # ATR is our 'Unit of Risk'. If ATR is 0, market is dead.
    atr = curr['atr'] if curr['atr'] > 0 else 0.0010
    
    # Define Recent Range (Last 20 candles)
    # This represents the "Battlefield" where bulls and bears fought.
    recent_high = df['high'].iloc[-21:-1].max()
    recent_low = df['low'].iloc[-21:-1].min()
    
    # --- LONG SETUP (BUY) ---
    # Rule 1: Trend is UP (Price > EMA 200)
    # Rule 2: Price BROKE the recent High (Breakout)
    # Rule 3: RSI is NOT Overbought (>70) - We don't want to FOMO at the top
    if (curr['close'] > curr['ema_200']) and \
       (curr['close'] > recent_high) and \
       (curr['rsi'] < 70):
           
           # Risk Management (The Holy Grail)
           # Stop Loss = 2 ATRs below price (Give it room to breathe)
           sl = curr['close'] - (atr * 2.0)
           
           # Take Profit = 3 ATRs above (Aim for 1.5 Risk:Reward Ratio minimum)
           # Or we let the 'manage_trades' function trail it.
           tp = curr['close'] + (atr * 4.0) 
           
           return 'BUY', sl, tp, 'TREND_RUNNER'

    # --- SHORT SETUP (SELL) ---
    # Rule 1: Trend is DOWN (Price < EMA 200)
    # Rule 2: Price BROKE the recent Low
    # Rule 3: RSI is NOT Oversold (<30)
    if (curr['close'] < curr['ema_200']) and \
       (curr['close'] < recent_low) and \
       (curr['rsi'] > 30):
           
           sl = curr['close'] + (atr * 2.0)
           tp = curr['close'] - (atr * 4.0)
           
           return 'SELL', sl, tp, 'TREND_RUNNER'

    return None, None, None, None

# ==============================================================================
# 🚦 GENERATOR
# ==============================================================================

def generate_signal(pair, broker, cloud):
    params = cloud.state['strategy_params']
    
    # 1. Fetch M15 Data (The Golden Timeframe)
    # We grab 300 candles to ensure EMA 200 is accurate
    df_m15 = broker.fetch_candles(pair, '15m', 300)
    
    if df_m15.empty: return None, None, None, None
    
    # 2. Calc
    df_m15 = calc_indicators(df_m15, params)
    
    # 3. Run Strategy
    return check_trend_runner(pair, df_m15, params)