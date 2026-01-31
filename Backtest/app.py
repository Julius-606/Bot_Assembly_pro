import streamlit as st
from datetime import datetime, timedelta
from src.backtester import BacktestEngine
from config import USER_DEFAULT_MARKETS

st.set_page_config(page_title="Darwin Backtest Lab 🧪", layout="wide")

st.title("🧬 Darwin Concoction Lab")
st.write("Modular Backtester: Testing parameters before going live.")

# Init the Engine
if 'engine' not in st.session_state:
    st.session_state.engine = BacktestEngine()

# --- CALIBRATION SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Calibrations")
    
    selected_pairs = st.multiselect("Pairs to Run", USER_DEFAULT_MARKETS, default=["EURUSD", "GBPUSD"])
    tf = st.selectbox("Timeframe", ["M5", "M15", "H1", "H4", "D1"], index=1)
    
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end = st.date_input("End Date", datetime.now())
        
    st.divider()
    
    st.write("🍱 **The Pantry**")
    menu = ["EMA", "RSI", "MACD", "Bol", "ADX", "SAR", "Ichi", "Donch", "Stoch", "WillR"]
    recipe = st.multiselect("Concoction Ingredients", menu, default=["EMA", "RSI", "ADX"])

# --- MAIN SHOW ---
if st.button("🚀 RUN BACKTEST SHOW"):
    success, msg = st.session_state.engine.startup()
    if not success:
        st.error(msg)
    else:
        st.toast("MT5 Connected. Time traveling...", icon="🕰️")
        
        for pair in selected_pairs:
            st.subheader(f"📊 Testing {pair}")
            prog = st.progress(0)
            status = st.empty()
            
            s_dt = datetime.combine(start, datetime.min.time())
            e_dt = datetime.combine(end, datetime.max.time())
            
            result = st.session_state.engine.run_concoction_test(pair, tf, s_dt, e_dt, recipe, prog)
            status.write(result)
            
        st.success("Test Show Finished. Check Google Sheets! 📈")
        st.session_state.engine.shutdown()