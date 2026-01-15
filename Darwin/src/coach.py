import os
import re
import json
import warnings
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
from src.cloud import CloudManager
from src.telegram_bot import TelegramBot
from src.strategy import STRATEGY_STATE # Read current state
from config import GEMINI_API_KEY

# 🔇 SILENCE THE GOOGLE WARNING
warnings.simplefilter(action='ignore', category=FutureWarning)

class Coach:
    """
    The Supervisor. 🧢
    Analyses game tape (history), benches players (pairs), 
    and adjusts the playbook (strategy.py) using AI.
    """
    def __init__(self):
        print("🧢 Coach: Initializing...")
        self.cloud = CloudManager()
        self.bot = TelegramBot()
        
        # Path to strategy.py (Assumes running from root dir)
        self.strategy_file = os.path.join("src", "strategy.py")
        
        # AI Setup
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            print("   ⚠️ No GEMINI_API_KEY found. Coach will use basic rules only.")
            self.model = None
            
        # Calibration Settings
        self.lookback_trades = 20 # Analyze last 20 CLOSED trades
        self.panic_threshold = 0.3 # If Win Rate < 30%, something is wrong
        self.bench_duration = 4 # Hours to bench a pair
        self.silence_threshold_hours = 24 # 💤 How long to wait before shouting at AI
        
        # 🛑 STRICT FILTER: Only look at these rows for analysis
        self.VALID_EXIT_REASONS = ['CLOSED_BY_BROKER', 'TP_HIT', 'SL_HIT', 'FRIDAY_CLOSE']

    def fetch_game_tape(self):
        """Reads trade history from Google Sheets via CloudManager."""
        print("   🧢 Coach: Reading Game Tape...")
        try:
            # We use the CloudManager's existing auth to get the sheet
            sheet = self.cloud.sheets_client.open_by_url(self.cloud.sheet_url) 
            ws = sheet.worksheet("Sheet3")
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            print(f"   ❌ Coach Error: Could not read sheets. {e}")
            return pd.DataFrame()

    def audit_performance(self):
        """
        Original hard-coded logic to audit pairs and bench them if they suck.
        This runs alongside the AI to ensure basic safety.
        """
        df = self.fetch_game_tape()
        if df.empty: return
        
        # Clean Data
        cols = ['PnL', 'Exit']
        for c in cols:
            # Force numeric, coercion turns errors to NaN
            df[c] = pd.to_numeric(df[c], errors='coerce')
        
        # 🔍 STRICT FILTERING: Only closed trades
        closed = df[df['Reason'].isin(self.VALID_EXIT_REASONS)]
        
        if closed.empty:
            print("   🧢 Coach: No closed trades to analyze yet.")
            return

        # 1. ANALYZE BY PAIR (Bench Logic)
        self.check_pairs(closed)
        
        # 2. Return the closed df for AI use
        return closed

    def check_pairs(self, df):
        """Checks for toxic pairs."""
        pairs = df['Pair'].unique()
        
        # Get currently benched pairs from the LIVE file state
        current_benched = STRATEGY_STATE.get("BENCHED_PAIRS", {})
        
        dirty = False # Flag if we need to write to file
        new_bench_state = current_benched.copy()

        # 1. Clean up old benching (Release the prisoners)
        now = datetime.now()
        for p, time_str in list(new_bench_state.items()):
            lift_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            if now > lift_time:
                print(f"   🔓 Lifting bench for {p}.")
                del new_bench_state[p]
                dirty = True

        # 2. Check for new offenders
        for pair in pairs:
            # Skip if already benched
            if pair in new_bench_state: continue

            # Get last X trades for this pair
            pair_data = df[df['Pair'] == pair].tail(self.lookback_trades)
            
            if len(pair_data) < 3: continue # Need sample size
            
            wins = len(pair_data[pair_data['PnL'] > 0])
            total = len(pair_data)
            win_rate = wins / total
            
            # THE BENCH RULE: < 30% Win Rate over last X trades
            if win_rate < self.panic_threshold:
                lift_time = now + timedelta(hours=self.bench_duration)
                lift_str = lift_time.strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"   🚨 BENCHING {pair} (WinRate: {win_rate:.2f}).")
                
                # Notify Boss
                self.bot.send_msg(f"🧢 COACH INTERVENTION\n🚫 Benching {pair}\n📉 WR: {int(win_rate*100)}% ({wins}/{total})\n⏳ Until: {lift_str}")
                
                new_bench_state[pair] = lift_str
                dirty = True

        # 3. Commit changes if needed
        if dirty:
            # Construct full state for update
            full_state = STRATEGY_STATE.copy()
            full_state["BENCHED_PAIRS"] = new_bench_state
            self._update_strategy_file(full_state)

    def check_activity(self):
        """
        Checks if the bot has been too quiet (no trades for X hours).
        Triggers AI to loosen the jar lid if needed.
        """
        # 1. Reload memory to get latest state from disk
        self.cloud.load_memory() 
        state = self.cloud.state
        
        # If we have open trades, we aren't silent. We are active.
        if len(state.get('open_bot_trades', [])) > 0:
            return

        # Check last history entry
        history = state.get('trade_history', [])
        if not history:
            return # Brand new bot, let it cook.

        last_trade = history[-1]
        last_time_str = last_trade.get('open_time', '')
        
        try:
            # Parse time (Format: "2023-10-27 10:00:00")
            last_entry = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_entry
            
            hours_silent = time_diff.total_seconds() / 3600
            
            # Threshold Check
            if hours_silent > self.silence_threshold_hours:
                print(f"   Note: Bot has been silent for {int(hours_silent)} hours.")
                self.handle_silence(hours_silent)
                
        except Exception as e:
            # Usually formatting error, ignore
            pass

    def handle_silence(self, hours):
        """
        Asks AI to tune parameters for higher frequency.
        """
        print("   🗣️ Silence Detected. Asking AI to increase sensitivity...")
        self.bot.send_msg(f"🗣️ SILENCE ALERT\nBot hasn't traded in {int(hours)} hours.\nConsulting AI to adjust strategy...")
        
        if not self.model:
            self.bot.send_msg("⚠️ ERROR: AI Key missing. Cannot adjust.")
            return

        current_strategy = json.dumps(STRATEGY_STATE, indent=2)
        
        prompt = f"""
        You are an expert Forex Algorithmic Trading Coach.
        
        CURRENT STRATEGY STATE:
        {current_strategy}
        
        PROBLEM:
        The bot has been silent (no new trades) for {int(hours)} hours.
        This means the current indicators are TOO STRICT or the filters are too tight for the current market volatility.
        
        TASK:
        Adjust the 'PARAMS' to be slightly MORE AGGRESSIVE/SENSITIVE to find entries.
        
        GUIDELINES:
        1. Do NOT change the 'ACTIVE_CONCOCTION' (Ingredients). Just tune the numbers.
        2. Example: Lower ADX threshold, Widen RSI limits, Reduce Moving Average periods.
        3. Make small, calculated adjustments. Do not go crazy.
        
        RESPONSE FORMAT:
        Return ONLY a raw JSON object representing the NEW STRATEGY_STATE. 
        Do not use Markdown formatting.
        """
        
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            new_state = json.loads(raw_text)
            
            if "ACTIVE_CONCOCTION" in new_state and "PARAMS" in new_state:
                print("   🧢 Oracle has updated parameters for activity.")
                self._update_strategy_file(new_state)
                self.bot.send_msg(f"✅ ADJUSTMENT APPLIED\nSettings loosened to find more trades.")
        except Exception as e:
            print(f"   ❌ Silence Fix Failed: {e}")

    def consult_oracle(self):
        """
        The AI Brain. 🧠
        Calculates Math FIRST. Then decides if AI consultation is needed.
        """
        # 1. Gather Data (Reuse the fetch from audit)
        closed_df = self.audit_performance()
        if closed_df is None or closed_df.empty: 
            return

        # CHECK: Only trigger reporting/AI every 20 trades
        total_closed = len(closed_df)
        if total_closed == 0 or total_closed % 20 != 0:
            return
            
        print(f"   🧢 Coach: 20-Trade Batch Completed ({total_closed} total). Analyzing Stats...")

        # 2. 🧮 DO THE MATH (Internal Analysis)
        recent_history = closed_df.tail(self.lookback_trades)
        
        wins = recent_history[recent_history['PnL'] > 0]
        losses = recent_history[recent_history['PnL'] <= 0]
        
        num_wins = len(wins)
        num_losses = len(losses)
        total_pnl = recent_history['PnL'].sum()
        
        win_rate = num_wins / len(recent_history) if len(recent_history) > 0 else 0
        
        # Basic Logic: Is the bot struggling?
        ai_assist_needed = (total_pnl < 0) or (win_rate < 0.40)
        
        # Prepare Report String
        active_concoction = STRATEGY_STATE.get("ACTIVE_CONCOCTION", [])
        report_msg = (
            f"🧢 COACH BATCH REPORT ({total_closed} Trades)\n"
            f"💰 Batch PnL: ${total_pnl:.2f}\n"
            f"🏆 Win Rate: {int(win_rate*100)}% ({num_wins}W / {num_losses}L)\n"
            f"🧪 Current Recipe: {active_concoction}\n"
        )

        # 3. DECISION GATE
        if not ai_assist_needed:
            print("   🧢 Performance is acceptable. AI consultation skipped.")
            self.bot.send_msg(report_msg + "✅ Status: HEALTHY. No Strategy changes needed.")
            return

        # --- SCENARIO: AI INTERVENTION NEEDED ---
        print("   🧢 Performance Alert! Consulting the Oracle (Gemini)...")
        report_msg += "⚠️ Status: UNDERPERFORMING. Consulting AI...\n"
        self.bot.send_msg(report_msg)

        if not self.model:
            self.bot.send_msg("⚠️ ERROR: AI Key missing. Cannot optimize.")
            return
        
        recent_history_json = recent_history.to_json(orient='records')
        current_strategy = json.dumps(STRATEGY_STATE, indent=2)
        
        prompt = f"""
        You are an expert Forex Algorithmic Trading Coach.
        
        CURRENT STRATEGY STATE:
        {current_strategy}
        
        RECENT CLOSED TRADE HISTORY (Last 20 Trades):
        {recent_history_json}
        
        TASK:
        The bot is underperforming (PnL < 0 or Win Rate < 40%).
        Analyze the losses and propose a NEW Strategy Configuration.
        
        1. CHANGE the 'ACTIVE_CONCOCTION' using ingredients from the 'MENU'.
        2. TWEAK 'PARAMS' to be more conservative or aggressive based on the market.
        3. STRICTLY limit ingredients to the provided 'MENU' list.
        4. Bench toxic pairs in 'BENCHED_PAIRS'.
        
        RESPONSE FORMAT:
        Return ONLY a raw JSON object representing the NEW STRATEGY_STATE. 
        Do not use Markdown formatting.
        Do not include explanations outside the JSON.
        """
        
        try:
            # 4. Ask AI
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            # Clean potential markdown code blocks
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            new_state = json.loads(raw_text)
            
            # 5. Validate Keys
            if "ACTIVE_CONCOCTION" in new_state and "PARAMS" in new_state:
                print("   🧢 Oracle has spoken. Applying updates...")
                self._update_strategy_file(new_state)
                
                new_recipe = new_state['ACTIVE_CONCOCTION']
                self.bot.send_msg(f"🧢 ORACLE UPDATE APPLIED\n🆕 New Recipe: {new_recipe}\n🧠 Strategy optimized for recovery.")
            else:
                print("   ⚠️ Oracle returned invalid JSON structure.")
                self.bot.send_msg("⚠️ AI Error: Invalid JSON response. Retrying next batch.")
                
        except Exception as e:
            print(f"   ❌ AI Optimization Failed: {e}")
            self.bot.send_msg(f"❌ AI Failed: {e}. Retrying next batch.")

    def _update_strategy_file(self, new_state_dict):
        """
        Surgically updates the STRATEGY_STATE in strategy.py
        """
        try:
            with open(self.strategy_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Python Syntax Conversion for the file
            # json.dumps gives "true", python needs "True"
            # We use json.dumps but then patch the booleans/nulls
            new_state_str = json.dumps(new_state_dict, indent=4)
            new_state_str = new_state_str.replace("true", "True").replace("false", "False").replace("null", "None")
            
            # Regex Magic 🪄
            start_marker = "# 🧠 AI EXCLUSIVE ZONE (Gemini edits this via Coach)"
            end_marker = "# 🛑 END AI ZONE"
            
            p_start = re.escape(start_marker)
            p_end = re.escape(end_marker)
            
            pattern = f"({p_start})(.*?)({p_end})"
            
            new_block = f"\n{start_marker}\n# The Coach (coach.py) uses Regex to surgically update this block.\n# ==============================================================================\nSTRATEGY_STATE = {new_state_str}\n# ==============================================================================\n{end_marker}"
            
            new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
            
            with open(self.strategy_file, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            print("   ✅ strategy.py successfully updated.")
            
        except Exception as e:
            print(f"   ❌ Failed to update strategy file: {e}")
            self.bot.send_msg(f"⚠️ COACH ERROR: Failed to write to file.\n{e}")

if __name__ == "__main__":
    c = Coach()
    # c.audit_performance() # Run classic audit
    c.consult_oracle()    # Run AI audit (which now includes audit)