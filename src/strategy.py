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
    """Calculates ADX (Average Directional Index) for Regime Filter."""
    if df.empty: return df
    
    n = params.get('REGIME_ADX_PERIOD', 14)
    
    # 1. True Range (TR)
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    
    # 2. Directional Movement (+DM, -DM)
    df['up'] = df['high'] - df['high'].shift(1)
    df['down'] = df['low'].shift(1) - df['low']
    
    df['pdm'] = np.where((df['up'] > df['down']) & (df['up'] > 0), df['up'], 0.0)
    df['mdm'] = np.where((df['down'] > df['up']) & (df['down'] > 0), df['down'], 0.0)
    
    # 3. Smoothing (Using EMA as approximation for Wilder's)
    # Wilder's Smoothing implies alpha = 1/n
    df['tr_s'] = df['tr'].ewm(alpha=1/n, adjust=False).mean()
    df['pdm_s'] = df['pdm'].ewm(alpha=1/n, adjust=False).mean()
    df['mdm_s'] = df['mdm'].ewm(alpha=1/n, adjust=False).mean()
    
    # 4. Directional Indexes (+DI, -DI)
    df['pdi'] = 100 * (df['pdm_s'] / df['tr_s'])
    df['mdi'] = 100 * (df['mdm_s'] / df['tr_s'])
    
    # 5. DX and ADX
    df['dx'] = 100 * abs(df['pdi'] - df['mdi']) / (df['pdi'] + df['mdi']).replace(0, 1)
    df['adx'] = df['dx'].ewm(alpha=1/n, adjust=False).mean()
    
    return df

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
        
        # 🛠️ FIX: Actually calculate ADX now
        df_m15 = calc_adx(df_m15, params)
        adx = df_m15['adx'].iloc[-1] if not df_m15.empty and 'adx' in df_m15.columns else 0
        
        # TRENDING REGIME
        if adx >= params['REGIME_ADX_THRESHOLD']:
            # Check SR_TREND
            df_m1 = broker.fetch_candles(pair, '1m', params['CANDLE_COUNT'])
            if df_m1.empty: return None, None, None, None
            
            # 🛠️ FIX: Calculate indicators for M1 data so 'bb_std' exists!
            df_m1 = calc_indicators(df_m1, params)

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
