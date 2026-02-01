import streamlit as st
from datetime import datetime, timedelta
from src.cloud import CloudManager
from config import USER_DEFAULT_MARKETS

# 🛡️ CLOUD GUARD: We do NOT import BacktestEngine here. 
# It lives on the VM worker only. MT5 is a Windows-only diva!

st.set_page_config(
    page_title="The Concoction Lab Cloud 🛰️",
    page_icon="🧪",
    layout="wide"
)

# --- CUSTOM CSS FOR THAT ALPHA VIBE ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #2e7bcf;
        color: white;
    }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #1e2130;
        border: 1px solid #3e4259;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🧪 The Concoction Lab (Cloud Edition)")
st.write("Commander, welcome back to the bridge. We've moved the logic to the cloud, but the execution stays on the ground. No cap, this is how hedge funds do it. 🏦✨")

# We initialize the CloudManager which is safe for Linux
if 'cloud' not in st.session_state:
    st.session_state.cloud = CloudManager()

# --- SYSTEM MONITORING ---
with st.expander("📡 System Status & Instructions", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("""
        **How this works:**
        1. You set the 'Mission' parameters here on the web.
        2. Press 'Deploy' to send the mission to the **Google Sheets Tasks** sheet.
        3. Your local Windows VM (running `worker.py`) picks it up and fires up MT5.
        4. Results are streamed back to your Google Sheets in real-time.
        """)
    with col_b:
        st.warning("""
        **Deployment Notes:**
        - If this app is stuck 'In the oven', verify your `requirements.txt` does NOT contain `MetaTrader5`.
        - Ensure your `.env` secrets are added to the Streamlit Cloud Dashboard.
        - The VM must be ON and the `worker.py` script must be running for trades to trigger.
        """)

st.divider()

# --- SIDEBAR: The Calibration Station ---
with st.sidebar:
    st.header("⚙️ Mission Calibration")
    st.write("Fine-tune the strategy before sending it to the front lines.")
    
    pairs = st.multiselect("Select Markets", USER_DEFAULT_MARKETS, default=["EURUSD", "GBPUSD", "XAUUSD"])
    tf = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1", "H4", "D1"], index=2)
    
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End", datetime.now())
    
    st.divider()
    
    st.write("⚖️ **Strictness Level**")
    st.caption("Higher strictness = more confluence needed (fewer, higher quality trades).")
    strictness = st.select_slider(
        "Level of confluence needed",
        options=["Low", "Medium", "High"],
        value="Medium"
    )
    
    st.divider()
    
    st.write("🧬 **Indicator Recipe**")
    menu = ["EMA", "RSI", "MACD", "Bol", "ADX", "SAR", "Ichi", "Kelt", "Donch", "Stoch", "CCI", "SMA", "WillR", "MFI", "ROC", "TRIX"]
    concoction = st.multiselect("Ingredients", menu, default=["EMA", "MACD", "Bol"])

# --- MAIN: Mission Control ---
st.subheader("🚀 Mission Control")

# Visual feedback for the current setup
if pairs:
    st.write(f"**Current Payload:** {len(pairs)} Pairs | {tf} Timeframe | {strictness} Strictness")
else:
    st.write("⚠️ *No pairs selected. Standing by...*")

if st.button("🔥 DEPLOY MISSION TO WORKER"):
    if not pairs:
        st.error("Commander, we can't trade thin air. Pick at least one pair! 🤡")
    else:
        with st.spinner("🛰️ Contacting C2 Center (Google Sheets)..."):
            # We request the task via Google Sheets
            success = st.session_state.cloud.request_task(
                pairs, tf, concoction, strictness, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d")
            )
            
            if success:
                st.success("✅ MISSION DEPLOYED! Your VM should be waking up now.")
                st.toast("Pips requested! 💰", icon="🚀")
                st.balloons()
                st.info("Head over to your Google Sheet 'Tasks' tab to watch the status change from PENDING to RUNNING.")
            else:
                st.error("❌ Failed to contact the C2 Center. Check your logs and API credentials.")

st.divider()
st.subheader("📊 Tactical Overview")
st.write("Check your Google Sheets for the full breakdown of Profit Factor, Win Rate, and Batch PnL.")
st.caption("Note: This UI is a remote control. Live performance graphs coming in v6.0! 🚀")