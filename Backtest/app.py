import streamlit as st
from datetime import datetime, timedelta
from src.cloud import CloudManager
from config import USER_DEFAULT_MARKETS

st.set_page_config(page_title="The Concoction Lab Cloud 🛰️", layout="wide")

st.title("🛰️ The Concoction Lab (Cloud Edition)")
st.write("Commander, pick your settings. The local VM will handle the heavy lifting. No cap.")

cloud = CloudManager()

# --- SIDEBAR: The Calibration Station ---
with st.sidebar:
    st.header("⚙️ Mission Settings")
    pairs = st.multiselect("Select Pairs", USER_DEFAULT_MARKETS, default=["EURUSD", "GBPUSD"])
    tf = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1", "H4", "D1"], index=2)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End", datetime.now())
    
    st.divider()
    st.write("⚖️ **Strictness Level**")
    strictness = st.select_slider("Confluence Needed", options=["Low", "Medium", "High"], value="Medium")
    
    st.divider()
    st.write("🧬 **Recipe**")
    menu = ["EMA", "RSI", "MACD", "Bol", "ADX", "SAR", "Ichi", "Kelt", "Donch", "Stoch", "CCI", "SMA", "WillR", "MFI", "ROC", "TRIX"]
    concoction = st.multiselect("Ingredients", menu, default=["EMA", "MACD", "Bol"])

# --- MAIN: Mission Control ---
if st.button("🚀 DEPLOY MISSION TO VM"):
    if not pairs:
        st.error("Pick at least one pair, chief.")
    else:
        success = cloud.request_task(
            pairs, tf, concoction, strictness, 
            start_date.strftime("%Y-%m-%d"), 
            end_date.strftime("%Y-%m-%d")
        )
        if success:
            st.success("🛰️ Mission Sent! The VM is firing up. Check your 'Tasks' sheet to watch the progress.")
            st.balloons()
        else:
            st.error("❌ Failed to contact the C2 Center.")

st.divider()
st.subheader("📋 Recent Tasks")
# You could add a 'cloud.get_all_tasks()' logic here to display a table of what's happening