import streamlit as st
from datetime import datetime, timedelta
from src.cloud import CloudManager
from config import USER_DEFAULT_MARKETS

# 🛡️ CLOUD GUARD: BacktestEngine is a Windows-only diva, so it stays on the VM.
# We just run the remote control here. 🎮

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
st.write("Commander, welcome back to the bridge. Execution stays on the ground, but the vision is in the cloud. No cap, we're institutional now. 🏦✨")

# Initialize the CloudManager (Safe for Linux/Streamlit Cloud)
if 'cloud' not in st.session_state:
    st.session_state.cloud = CloudManager()

# --- SYSTEM MONITORING ---
with st.expander("📡 System Status & Instructions", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("""
        **Mission Protocol:**
        1. Set your 'Mission' parameters.
        2. 'Deploy' to send orders to the **Google Sheets Tasks**.
        3. Your local Windows VM (running `worker.py`) fires up MT5.
        4. Results stream back to the Motherboard in real-time.
        """)
    with col_b:
        # Check Cloud Auth Status - Real-time connectivity check
        if st.session_state.cloud.authenticated:
            st.success("🛰️ C2 LINK: ONLINE (Service Account is vibing)")
        else:
            st.error(f"🛰️ C2 LINK: OFFLINE ({st.session_state.cloud.last_error})")
            
        st.warning("""
        **Deployment Notes:**
        - VM must be ON and `worker.py` must be active.
        - Ensure `.env` secrets are mirrored in Streamlit Cloud Dashboard.
        """)

st.divider()

# --- SIDEBAR: The Calibration Station ---
with st.sidebar:
    st.header("⚙️ Mission Calibration")
    st.write("Fine-tune the strategy before sending it to the front lines.")
    
    pairs = st.multiselect("Select Markets", USER_DEFAULT_MARKETS, default=["EURUSD", "GBPUSD", "XAUUSD"])
    
    # M30 is officially in the building! 📉
    tf = st.selectbox("Timeframe", ["M1", "M5", "M15", "M30", "H1", "H4", "D1"], index=3)
    
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End", datetime.now())
    
    st.divider()
    
    st.write("⚖️ **Strictness Level**")
    st.caption("Higher strictness = more confluence needed. Don't be a gambler. 🤡")
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
    st.write("⚠️ *No pairs selected. Standing by for orders...*")

if st.button("🔥 DEPLOY MISSION TO WORKER"):
    if not pairs:
        st.error("Commander, we can't trade thin air. Pick at least one pair! 🤡")
    else:
        with st.spinner("🛰️ Contacting C2 Center (Google Sheets)..."):
            # The 'Snitch' returns success and the actual error if things go south
            success, error_msg = st.session_state.cloud.request_task(
                pairs, tf, concoction, strictness, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d")
            )
            
            if success:
                st.success("✅ MISSION DEPLOYED! Check the 'Tasks' sheet to watch it go.")
                st.toast("Pips requested! 💰", icon="🚀")
                st.balloons()
            else:
                st.error("❌ Failed to contact the C2 Center.")
                with st.expander("🛠️ Debug Info (The Snitch's Report)"):
                    st.code(error_msg)
                    if "PERMISSION_DENIED" in error_msg:
                        st.write("💡 Bruh, you gotta share the Google Sheet with the Service Account email as an **Editor**.")
                    elif "API_KEY_SERVICE_DISABLED" in error_msg:
                        st.write("💡 You need to enable the **Google Sheets API** AND the **Google Drive API** in your Google Cloud Console.")

st.divider()
st.subheader("📊 Tactical Overview")
st.write("Head to your Google Sheet for the Profit Factor, Win Rate, and Batch PnL breakdown.")
st.caption("Note: Live performance graphs coming in v6.0! Stay tuned. 🚀")