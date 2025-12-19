import pandas as pd
import numpy as np

# ==============================================================================
# 🧠 INDICATORS
# ==============================================================================

def calc_indicators(df, params):
    if df.empty: return df # Safety check
    
    # RSI
    p = params['MR_RSI_PERIOD']
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=p).mean().replace(0, 1e-10)
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs)).fillna(50)
    
    # MACD
    f, s, sig = params['MOMO_MACD_FAST'], params['MOMO_MACD_SLOW'], params['MOMO_MACD_SIGNAL']
    df['ema_fast'] = df['close'].ewm(span=f).mean()
    df['ema_slow'] = df['close'].ewm(span=s).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_signal'] = df['macd'].ewm(span=sig).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # BB
    bp, bs = params['MR_BB_PERIOD'], params['MR_BB_STD_DEV']
    df['bb_mid'] = df['close'].rolling(window=bp).mean()
    df['bb_std'] = df['close'].rolling(window=bp).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * bs)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * bs)

    return df

def calc_adx(df, params):
    # Simplified ADX calc for regime filter
    return df # Placeholder if actual ADX logic is missing in snippet

def check_sr_trend(pair, df_m1, df_m5, broker, params):
    # Logic for trend trading
    return None

def check_scalper(pair, df_m5, broker, params):
    # Logic for scalping
    return None

def check_mean_revert(pair, df_m5, broker, params):
    # Logic for mean reversion
    return None

def generate_signal(pair, broker, cloud):
    strat = cloud.state.get('active_strategy', 'Auto')
    params = cloud.state['strategy_params']
    
    # 1. Fetch Data
    df_m5 = broker.fetch_candles(pair, '5m', 50)
    if df_m5.empty: return None, None, None, None # Safety Return
    
    df_m5 = calc_indicators(df_m5, params)
    
    # 2. Router
    if strat == 'Auto':
        # Check Regime (ADX on M15)
        df_m15 = broker.fetch_candles(pair, '15m', 50)
        if df_m15.empty: return None, None, None, None
        
        df_m15 = calc_adx(df_m15, params)
        adx = df_m15['adx'].iloc[-1] if not df_m15.empty else 0
        
        # TRENDING REGIME
        if adx >= params['REGIME_ADX_THRESHOLD']:
            # Check SR_TREND
            df_m1 = broker.fetch_candles(pair, '1m', params['CANDLE_COUNT'])
            res = check_sr_trend(pair, df_m1, df_m5, broker, params)
            if res: return res
            
            # Check SCALPER
            res = check_scalper(pair, df_m5, broker, params)
            if res: return res
            return None, None, None, None
        # RANGING REGIME
        else:
            # RANGING REGIME
            res = check_mean_revert(pair, df_m5, broker, params)
            if res: return res
            return None, None, None, None
            
    return None, None, None, None