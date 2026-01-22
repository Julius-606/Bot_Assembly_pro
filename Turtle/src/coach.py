import os
import re
import json
import warnings
import pandas as pd
import importlib 
import time
import google.generativeai as genai
from datetime import datetime, timedelta
from src.cloud import CloudManager
from src.telegram_bot import TelegramBot
import src.strategy as strategy_module 
from config import GEMINI_API_KEYS # 🛠️ Import List, not single key

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
        
        # 🛠️ PATHING FIX: Locate strategy.py relative to coach.py (same folder)
        # This prevents "File Not Found" errors if running from different dirs
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.strategy_file = os.path.join(current_dir, "strategy.py")
        
        # AI Setup (Multi-Key)
        self.api_keys = GEMINI_API_KEYS
        self.current_key_index = 0
        self.model = None
        self.model_name = "gemini-1.5-flash" # Default fallback
        
        if self.api_keys:
            self._initialize_ai()
        else:
            print("   ⚠️ No GEMINI_API_KEYS found. Coach will use basic rules only.")
            
        # Calibration Settings
        self.lookback_trades = 20 # Analyze last 20 CLOSED trades
        self.panic_threshold = 0.3 # If Win Rate < 30%, something is wrong
        self.bench_duration = 4 # Hours to bench a pair
        self.silence_threshold_hours = 24 # 💤 How long to wait before shouting at AI
        
        # 🛑 STRICT FILTER: Only look at these rows for analysis
        self.VALID_EXIT_REASONS = ['CLOSED_BY_BROKER', 'TP_HIT', 'SL_HIT', 'FRIDAY_CLOSE']

    def _initialize_ai(self):
        """Sets up the generative model with the current key."""
        try:
            current_key = self.api_keys[self.current_key_index]
            # Mask key for logging safety
            masked_key = current_key[:4] + "..." + current_key[-4:]
            print(f"   🔑 Loading AI Key [{self.current_key_index + 1}/{len(self.api_keys)}]: {masked_key}")
            
            genai.configure(api_key=current_key)
            
            # Resolve model name (only do this once or if model is None)
            if not self.model:
                resolved = self._resolve_model_name()
                if resolved: self.model_name = resolved
            
            self.model = genai.GenerativeModel(self.model_name)
            
        except Exception as e:
            print(f"   ⚠️ AI Init Failed for key {self.current_key_index}: {e}")

    def _rotate_key(self):
        """Switches to the next available API Key."""
        if not self.api_keys: return False
        
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"   🔄 Rotating to API Key #{self.current_key_index + 1}...")
        
        # 🛠️ CRITICAL FIX: Reset model to force re-resolution for the new key
        # This prevents Key #2 from trying to use a broken model that Key #1 selected.
        self.model = None 
        
        self._initialize_ai()
        return True

    def _generate_safe(self, prompt):
        """
        The Bulletproof Generator. 🛡️
        Tries to generate content. If Quota Exceeded (429) OR Invalid Key (400), rotates keys.
        """
        if not self.model: return None

        max_retries = len(self.api_keys) + 1
        attempts = 0

        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                return response
            except Exception as e:
                error_str = str(e).lower()
                
                # 🛠️ VERBOSE ERROR LOGGING: Print exactly why we are rotating
                # Catch 429 (Quota), 400 (Invalid), 403 (Permission), 503 (Overload)
                triggers = ["429", "quota", "resource", "key not valid", "400", "403"]
                
                if any(x in error_str for x in triggers):
                    print(f"   ⚠️ Key Issue (#{self.current_key_index + 1}).")
                    print(f"      ↳ Reason: {e}") # <--- 🗣️ THE SNITCH
                    print("      ↳ Rotating...")
                    
                    self._rotate_key()
                    attempts += 1
                    time.sleep(5) # 🛠️ Increased cooldown to 5s to let quotas settle
                else:
                    # Genuine error (like bad prompt), don't retry infinite
                    print(f"   ❌ AI Generation Error (Non-Rotatable): {e}")
                    return None
        
        print("   💀 All API Keys exhausted. AI unavailable.")
        self.bot.send_msg("💀 FATAL: All AI Keys have failed.")
        return None

    def _resolve_model_name(self):
        """
        Dynamically finds the best available Gemini model.
        """
        try:
            # List all models
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            # Priority Queue
            # 🛠️ REMOVED '2.0-flash-exp' because it causes Limit: 0 errors
            priorities = [
                'models/gemini-1.5-flash',
                'models/gemini-1.5-flash-latest',
                'models/gemini-1.5-pro',
                'models/gemini-pro'
            ]
            
            for p in priorities:
                if p in available_models:
                    # print(f"   ✅ AI Model Selected: {p}")
                    return p.replace("models/", "")

            # Fallback
            for m in available_models:
                if 'gemini' in m:
                    return m.replace("models/", "")
            
            return None

        except Exception as e:
            # If resolve fails (likely due to invalid key), we default. 
            # If the key is truly invalid, _generate_safe will catch the 400 error later and rotate.
            print(f"   ⚠️ Model Discovery Failed: {e}. Defaulting to 'gemini-1.5-flash'.")
            return 'gemini-1.5-flash'

    def get_current_strategy_state(self):
        """Forces a reload of the strategy module to get fresh state from disk."""
        try:
            importlib.reload(strategy_module)
            return strategy_module.STRATEGY_STATE
        except Exception as e:
            print(f"   ⚠️ Coach Error: Could not reload strategy state. {e}")
            return strategy_module.STRATEGY_STATE

    def fetch_game_tape(self):
        """Reads trade history from Google Sheets via CloudManager."""
        print("   🧢 Coach: Reading Game Tape...")
        try:
            # We use the CloudManager's existing auth to get the sheet
            sheet = self.cloud.sheets_client.open_by_url(self.cloud.sheet_url) 
            ws = sheet.worksheet("Sheet2")
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            print(f"   ❌ Coach Error: Could not read sheets. {e}")
            return pd.DataFrame()

    def audit_performance(self):
        """Runs the full audit cycle."""
        df = self.fetch_game_tape()
        if df.empty: return

        # 🧹 CLEANUP
        df.columns = df.columns.str.strip()
        
        # 🛡️ LESS STRICT CHECK
        required_columns = ['PnL', 'Exit', 'Reason', 'Pair']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            print(f"   ⚠️ Coach Warning: Missing columns {missing} in Google Sheet.")
            return 
        
        # Clean Data
        cols = ['PnL', 'Exit']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        
        # 🔍 STRICT FILTERING
        if 'Reason' in df.columns:
            closed = df[df['Reason'].isin(self.VALID_EXIT_REASONS)]
        else:
            return

        if closed.empty:
            print("   🧢 Coach: No closed trades to analyze yet.")
            return

        self.check_pairs(closed)
        return closed

    def diagnose(self):
        """Returns a quick health check string for the user."""
        print("   🧢 Coach: Running Diagnostics (Read-Only)...")
        
        model_name = self.model_name if self.model else "None"
        ai_status = f"✅ Online ({model_name} | Key #{self.current_key_index+1})" if self.model else "❌ Offline"
        
        state = self.get_current_strategy_state()
        benched = state.get("BENCHED_PAIRS", {})
        
        bench_msg = ""
        if benched:
            bench_msg = "\n🚫 BENCHED PAIRS:\n"
            for pair, time_str in benched.items():
                bench_msg += f"   - {pair} until {time_str}\n"
        else:
            bench_msg = "\n✅ No pairs currently benched."

        df = self.fetch_game_tape()
        
        if df is None or df.empty:
            return (f"🧢 COACH DIAGNOSTICS\n"
                    f"🧠 AI Brain: {ai_status}\n"
                    f"⚠️ Sheet Status: Connected, but Sheet is EMPTY.")

        df.columns = df.columns.str.strip()
        required_columns = ['PnL', 'Exit', 'Reason', 'Pair']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
             return (f"🧢 COACH DIAGNOSTICS\n"
                    f"🧠 AI Brain: {ai_status}\n"
                    f"❌ Sheet Error: Missing Columns {missing}.\n")

        for c in ['PnL', 'Exit']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            
        closed = df[df['Reason'].isin(self.VALID_EXIT_REASONS)] if 'Reason' in df.columns else pd.DataFrame()
        
        if closed.empty:
             return (f"🧢 COACH DIAGNOSTICS\n"
                    f"🧠 AI Brain: {ai_status}\n"
                    f"⚠️ Data Status: No CLOSED trades found.\n"
                    f"{bench_msg}")

        # Stats
        count = len(closed)
        remainder = count % 20
        trades_needed = 20 - remainder
        recent_30 = closed.tail(30)
        total_30 = len(recent_30)
        wins = len(recent_30[recent_30['PnL'] > 0])
        win_rate = (wins / total_30 * 100) if total_30 > 0 else 0
        gross_profit = recent_30[recent_30['PnL'] > 0]['PnL'].sum()
        gross_loss = abs(recent_30[recent_30['PnL'] < 0]['PnL'].sum())
        profit_factor = f"{gross_profit / gross_loss:.4f}" if gross_loss != 0 else "∞"
        
        return (f"🧢 COACH DIAGNOSTICS\n"
                f"🧠 AI Brain: {ai_status}\n"
                f"📊 Batch Progress: {remainder}/20 collected\n"
                f"⏳ Next Review: In {trades_needed} trades\n"
                f"📜 Total History: {count} closed trades\n"
                f"-----------------------------\n"
                f"📉 LAST 30 TRADES SNAPSHOT\n"
                f"🏆 Win Rate: {win_rate:.2f}%\n"
                f"⚖️ Profit Factor: {profit_factor}\n"
                f"{bench_msg}")

    def check_pairs(self, df):
        """Checks for toxic pairs and updates strategy file."""
        pairs = df['Pair'].unique()
        state = self.get_current_strategy_state()
        current_benched = state.get("BENCHED_PAIRS", {})
        
        dirty = False
        new_bench_state = current_benched.copy()

        # 1. Clean up old benching
        now = datetime.now()
        for p, time_str in list(new_bench_state.items()):
            try:
                lift_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                if now > lift_time:
                    print(f"   🔓 Lifting bench for {p}.")
                    del new_bench_state[p]
                    dirty = True
            except:
                del new_bench_state[p]
                dirty = True

        # 2. Check for new offenders
        for pair in pairs:
            if pair in new_bench_state: continue

            pair_data = df[df['Pair'] == pair].tail(self.lookback_trades)
            if len(pair_data) < 3: continue 
            
            wins = len(pair_data[pair_data['PnL'] > 0])
            total = len(pair_data)
            win_rate = wins / total
            
            if win_rate < self.panic_threshold:
                lift_time = now + timedelta(hours=self.bench_duration)
                lift_str = lift_time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   🚨 BENCHING {pair} (WinRate: {win_rate:.2f}).")
                self.bot.send_msg(f"🧢 COACH INTERVENTION\n🚫 Benching {pair}\n📉 WR: {int(win_rate*100)}% ({wins}/{total})\n⏳ Until: {lift_str}")
                new_bench_state[pair] = lift_str
                dirty = True

        if dirty:
            full_state = state.copy()
            full_state["BENCHED_PAIRS"] = new_bench_state
            self._update_strategy_file(full_state)

    def check_activity(self):
        """Checks if bot is too silent."""
        self.cloud.load_memory() 
        state = self.cloud.state
        if len(state.get('open_bot_trades', [])) > 0: return

        history = state.get('trade_history', [])
        if not history: return 

        last_trade = history[-1]
        try:
            last_entry = datetime.strptime(last_trade.get('open_time', ''), "%Y-%m-%d %H:%M:%S")
            hours_silent = (datetime.now() - last_entry).total_seconds() / 3600
            
            if hours_silent > self.silence_threshold_hours:
                print(f"   Note: Bot has been silent for {int(hours_silent)} hours.")
                self.handle_silence(hours_silent)
        except:
            pass

    def handle_silence(self, hours):
        print("   🗣️ Silence Detected. Asking AI to increase sensitivity...")
        self.bot.send_msg(f"🗣️ SILENCE ALERT\nBot hasn't traded in {int(hours)} hours.\nConsulting AI to adjust strategy...")
        
        state = self.get_current_strategy_state()
        current_strategy = json.dumps(state, indent=2)
        
        prompt = f"""
        You are an expert Forex Algorithmic Trading Coach.
        CURRENT STRATEGY STATE: {current_strategy}
        PROBLEM: Bot has been silent for {int(hours)} hours.
        TASK: Adjust 'PARAMS' to be MORE AGGRESSIVE/SENSITIVE to find entries.
        RESPONSE FORMAT: JSON ONLY of the new STRATEGY_STATE.
        """
        
        response = self._generate_safe(prompt)
        if not response: return

        try:
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            new_state = json.loads(raw_text)
            
            if "ACTIVE_CONCOCTION" in new_state and "PARAMS" in new_state:
                print("   🧢 Oracle has updated parameters for activity.")
                self._update_strategy_file(new_state)
                self.bot.send_msg(f"✅ ADJUSTMENT APPLIED\nSettings loosened to find more trades.")
        except Exception as e:
            print(f"   ❌ Silence Fix Failed: {e}")

    def consult_oracle(self, force=False):
        """The AI Brain with Key Rotation."""
        closed_df = self.audit_performance()
        if closed_df is None or closed_df.empty: 
            if force: self.bot.send_msg("⚠️ Consult failed: No closed trades found to analyze.")
            return

        total_closed = len(closed_df)
        if not force and (total_closed == 0 or total_closed % 20 != 0):
            return
            
        print(f"   🧢 Coach: {'FORCED ' if force else ''}Batch Analysis ({total_closed} total)...")

        recent_history = closed_df.tail(self.lookback_trades)
        wins = recent_history[recent_history['PnL'] > 0]
        losses = recent_history[recent_history['PnL'] <= 0]
        win_rate = len(wins) / len(recent_history) if len(recent_history) > 0 else 0
        total_pnl = recent_history['PnL'].sum()
        
        ai_assist_needed = (total_pnl < 0) or (win_rate < 0.40) or force
        state = self.get_current_strategy_state()
        active_concoction = state.get("ACTIVE_CONCOCTION", [])
        
        report_msg = (
            f"🧢 COACH BATCH REPORT ({total_closed} Trades)\n"
            f"💰 Batch PnL: ${total_pnl:.2f}\n"
            f"🏆 Win Rate: {int(win_rate*100)}%\n"
            f"🧪 Recipe: {active_concoction}\n"
        )

        if not ai_assist_needed:
            print("   🧢 Performance is acceptable. AI consultation skipped.")
            self.bot.send_msg(report_msg + "✅ Status: HEALTHY.")
            return

        print("   🧢 Performance Alert! Consulting the Oracle (Gemini)...")
        self.bot.send_msg(report_msg + "⚠️ Status: UNDERPERFORMING (or Forced). Consulting AI...")

        recent_history_json = recent_history.to_json(orient='records')
        current_strategy = json.dumps(state, indent=2)
        
        prompt = f"""
        You are an expert Forex Algorithmic Trading Coach.
        CURRENT STRATEGY STATE: {current_strategy}
        RECENT HISTORY: {recent_history_json}
        TASK: Bot is underperforming. Propose NEW Strategy Configuration.
        1. CHANGE 'ACTIVE_CONCOCTION' from 'MENU'.
        2. TWEAK 'PARAMS'.
        3. STRICTLY limit ingredients to 'MENU'.
        RESPONSE FORMAT: JSON ONLY of the new STRATEGY_STATE.
        """
        
        response = self._generate_safe(prompt)
        if not response: return
        
        try:
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            new_state = json.loads(raw_text)
            
            if "ACTIVE_CONCOCTION" in new_state and "PARAMS" in new_state:
                print("   🧢 Oracle has spoken. Applying updates...")
                self._update_strategy_file(new_state)
                new_recipe = new_state['ACTIVE_CONCOCTION']
                self.bot.send_msg(f"🧢 ORACLE UPDATE APPLIED\n🆕 New Recipe: {new_recipe}\n🧠 Strategy optimized.")
            else:
                self.bot.send_msg("⚠️ AI Error: Invalid JSON response.")
        except Exception as e:
            print(f"   ❌ AI Optimization Failed: {e}")
            self.bot.send_msg(f"❌ AI Failed: {e}")

    def _update_strategy_file(self, new_state_dict):
        """Surgically updates strategy.py"""
        try:
            with open(self.strategy_file, "r", encoding="utf-8") as f:
                content = f.read()

            new_state_str = json.dumps(new_state_dict, indent=4)
            new_state_str = new_state_str.replace("true", "True").replace("false", "False").replace("null", "None")
            
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
    c.consult_oracle()