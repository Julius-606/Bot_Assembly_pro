import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Trading Bot Analytics", page_icon="📈", layout="wide")

st.title("🤖 Algorithmic Trading Bot Performance Hub")

# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload Trade CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    # Fallback to local default if present
    try:
        df = pd.read_csv("Brain_Nursery_Sheet1.csv")
        st.sidebar.info("Loaded default dataset: Brain_Nursery_Sheet1.csv")
    except Exception:
        st.warning("Please upload a CSV file with your trading history.")
        st.stop()

# Ensure standard column names and types
df.columns = [col.strip() for col in df.columns]
required_cols = ["Strategy", "Pair", "PnL", "Close Time"]

if not all(col in df.columns for col in required_cols):
    st.error(f"CSV is missing one of the required columns: {required_cols}")
    st.stop()

df["PnL"] = pd.to_numeric(df["PnL"], errors="coerce").fillna(0.0)
df["Close Time"] = pd.to_datetime(df["Close Time"], errors="coerce")
df = df.sort_values(by="Close Time").reset_index(drop=True)

# Bot / Strategy Selector
strategies = sorted(df["Strategy"].dropna().unique().tolist())
selected_bot = st.sidebar.selectbox("Select Bot Strategy:", strategies)

# Filter Data for Selected Bot
bot_df = df[df["Strategy"] == selected_bot].copy()

if bot_df.empty:
    st.warning("No trades found for the selected strategy.")
    st.stop()

# -------------------------------------------------------------
# 1. METRICS & SUMMARY TABLE
# -------------------------------------------------------------
total_trades = len(bot_df)
winning_trades = int((bot_df["PnL"] > 0).sum())
losing_trades = int((bot_df["PnL"] < 0).sum())
win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

total_profit = bot_df[bot_df["PnL"] > 0]["PnL"].sum()
total_loss = bot_df[bot_df["PnL"] < 0]["PnL"].sum()
net_profit = bot_df["PnL"].sum()
profit_factor = (total_profit / abs(total_loss)) if abs(total_loss) > 0 else 0.0

# Calculate active weeks
if bot_df["Close Time"].notna().sum() > 1:
    total_days = (bot_df["Close Time"].max() - bot_df["Close Time"].min()).days
    weeks_active = max(round(total_days / 7, 1), 1.0)
else:
    weeks_active = 1.0
weekly_avg = net_profit / weeks_active

st.subheader(f"📊 Performance Overview: {selected_bot}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Trades", total_trades)
col2.metric("Win Rate", f"{win_rate:.1f}%")
col3.metric("Net Profit", f"${net_profit:,.2f}")
col4.metric("Profit Factor", f"{profit_factor:.2f}")
col5.metric("Weekly Avg", f"${weekly_avg:,.2f}")

# Detail Metrics Table
summary_data = {
    "Metric": [
        "Total Trades", "Winning Trades", "Losing Trades", "Win Rate (%)",
        "Total Profit ($)", "Total Loss ($)", "Net Profit ($)", 
        "Profit Factor", "Weeks Active", "Weekly Average ($)"
    ],
    "Value": [
        f"{total_trades}", f"{winning_trades}", f"{losing_trades}", f"{win_rate:.2f}%",
        f"${total_profit:,.2f}", f"${total_loss:,.2f}", f"${net_profit:,.2f}",
        f"{profit_factor:.2f}", f"{weeks_active}", f"${weekly_avg:,.2f}"
    ]
}
st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

st.markdown("---")

# -------------------------------------------------------------
# 2. CUMULATIVE NET PROFIT LINE GRAPH
# -------------------------------------------------------------
st.subheader("📈 Cumulative Net Profit Over Time")
bot_df["Cumulative_PnL"] = bot_df["PnL"].cumsum()

fig_line = px.line(
    bot_df,
    x="Close Time",
    y="Cumulative_PnL",
    title=f"{selected_bot} - Equity Growth Curve",
    markers=True,
    labels={"Close Time": "Date & Time", "Cumulative_PnL": "Cumulative PnL ($)"}
)
fig_line.update_traces(line_color="#00CC96", line_width=2.5)
st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# -------------------------------------------------------------
# 3. BAR GRAPH: PAIRS VS TRADE COUNT
# -------------------------------------------------------------
st.subheader("📊 Trade Count by Currency Pair")
pair_counts = bot_df["Pair"].value_counts().reset_index()
pair_counts.columns = ["Pair", "Trade Count"]

fig_bar = px.bar(
    pair_counts,
    x="Pair",
    y="Trade Count",
    text="Trade Count",
    title=f"Total Trades Taken per Pair ({selected_bot})",
    color="Trade Count",
    color_continuous_scale="Viridis"
)
fig_bar.update_traces(textposition="outside")
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# -------------------------------------------------------------
# 4. PIE CHARTS: PROFIT & LOSS BREAKDOWN (GOING DOWN)
# -------------------------------------------------------------
st.subheader("🥧 Pair Breakdown: Profits & Losses")

# Profit Share Pie Chart
profit_df = bot_df[bot_df["PnL"] > 0].groupby("Pair")["PnL"].sum().reset_index()
if not profit_df.empty:
    fig_profit_pie = px.pie(
        profit_df,
        names="Pair",
        values="PnL",
        title="Net Profit Distribution by Pair (%)",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_profit_pie.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_profit_pie, use_container_width=True)
else:
    st.info("No profitable trades logged for this strategy yet.")

# Loss Share Pie Chart (Placed directly below)
loss_df = bot_df[bot_df["PnL"] < 0].groupby("Pair")["PnL"].apply(lambda x: abs(x.sum())).reset_index()
loss_df.rename(columns={"PnL": "Loss"}, inplace=True)

if not loss_df.empty:
    fig_loss_pie = px.pie(
        loss_df,
        names="Pair",
        values="Loss",
        title="Net Loss Distribution by Pair (%)",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_loss_pie.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_loss_pie, use_container_width=True)
else:
    st.info("No losing trades logged for this strategy (100% win rate or zero trades).")