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
        self.lookback_trades = 20 # Analyze last 20 trades per pair
        self.panic_threshold = 0.3 # If Win Rate < 30%, something is wrong
        self.bench_duration = 4 # Hours to bench a pair

    def fetch_game_tape(self):
        """Reads trade history from Google Sheets via CloudManager."""
        print("   🧢 Coach: Reading Game Tape...")
        try:
            # We use the CloudManager's existing auth to get the sheet
            sheet = self.cloud.sheets_client.open_by_url(self.cloud.sheet_url) 
            ws = sheet.worksheet("Trade_Logs")
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
        
        # Filter for recent closed trades only
        closed = df[df['Reason'].isin(['CLOSED_BY_BROKER', 'TP_HIT', 'SL_HIT', 'FRIDAY_CLOSE'])]
        
        if closed.empty:
            print("   🧢 Coach: No closed trades to analyze yet.")
            return

        # 1. ANALYZE BY PAIR (Bench Logic)
        self.check_pairs(closed)

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

    def consult_oracle(self):
        """
        The AI Brain. 🧠
        Sends trade history to Gemini and asks for strategy updates.
        """
        if not self.model: 
            print("   🧢 AI Missing. Skipping optimization.")
            return

        print("   🧢 Coach: Consulting the Oracle (Gemini)...")
        
        # 1. Gather Data
        df = self.fetch_game_tape()
        if df.empty or len(df) < 5: 
            print("   🧢 Not enough data for AI yet.")
            return

        # Filter for recent closed trades
        closed = df[df['Reason'].isin(['CLOSED_BY_BROKER', 'TP_HIT', 'SL_HIT'])]
        recent_history = closed.tail(self.lookback_trades).to_json(orient='records')
        
        # 2. Construct Prompt
        current_strategy = json.dumps(STRATEGY_STATE, indent=2)
        
        prompt = f"""
        You are an expert Forex Algorithmic Trading Coach.
        
        CURRENT STRATEGY STATE:
        {current_strategy}
        
        RECENT TRADE HISTORY (JSON):
        {recent_history}
        
        TASK:
        Analyze recent performance to find the BEST POSSIBLE TRADING COMBINATION.
        1. If PnL is positive, optimize 'PARAMS' for better efficiency.
        2. If PnL is negative or stagnant, change the 'ACTIVE_CONCOCTION' using ingredients from the 'MENU'.
        3. STRICTLY limit ingredients to the provided 'MENU' list.
        4. Bench toxic pairs in 'BENCHED_PAIRS'.
        
        RESPONSE FORMAT:
        Return ONLY a raw JSON object representing the NEW STRATEGY_STATE. 
        Do not use Markdown formatting.
        Do not include explanations outside the JSON.
        """
        
        try:
            # 3. Ask AI
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            # Clean potential markdown code blocks
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            new_state = json.loads(raw_text)
            
            # 4. Validate Keys
            if "ACTIVE_CONCOCTION" in new_state and "PARAMS" in new_state:
                print("   🧢 Oracle has spoken. Applying updates...")
                self._update_strategy_file(new_state)
                self.bot.send_msg(f"🧠 AI UPDATE APPLIED\nRecipe: {new_state['ACTIVE_CONCOCTION']}")
            else:
                print("   ⚠️ Oracle returned invalid JSON structure.")
                
        except Exception as e:
            print(f"   ❌ AI Optimization Failed: {e}")

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
            start_marker = "# 🧠 AI EXCLUSIVE ZONE (DO NOT EDIT MANUALLY)"
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
    c.audit_performance() # Run classic audit
    c.consult_oracle()    # Run AI audit