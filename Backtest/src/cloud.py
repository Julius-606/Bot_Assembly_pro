import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_DICT, SHEET_URL, USER_DEFAULT_MARKETS
from datetime import datetime

class CloudManager:
    """The Chief Aesthetic Officer 🎨. Handles the Google Sheets C2 connection."""
    def __init__(self):
        self.client = None
        self.setup()

    def setup(self):
        if not GOOGLE_CREDS_DICT or "client_email" not in GOOGLE_CREDS_DICT:
            print("❌ Cloud Setup Aborted: Missing Credentials in Config.")
            return
            
        try:
            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT, 
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets", 
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            self.client = gspread.authorize(creds)
            print("🛰️ Cloud C2 Link Established.")
        except Exception as e:
            print(f"❌ Cloud Setup Failed: {e}")

    # --- 🛰️ REMOTE TASKING LOGIC (Commander to Worker) ---
    def request_task(self, pairs, tf, recipe, strictness, start_date, end_date):
        """Commander (Cloud) calls this to drop a mission into the sheet."""
        if not self.client:
            print("❌ Cannot request task: Not authenticated.")
            return False
            
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try:
                ws = sheet.worksheet("Tasks")
            except:
                # Create the Tasks mission board if it doesn't exist
                ws = sheet.add_worksheet(title="Tasks", rows="1000", cols="10")
                ws.append_row(["Timestamp", "Status", "Pairs", "TF", "Recipe", "Strictness", "Start", "End"])
            
            ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "PENDING",
                ",".join(pairs),
                tf,
                "+".join(recipe),
                strictness,
                start_date,
                end_date
            ])
            return True
        except Exception as e:
            print(f"❌ Could not request task: {e}")
            return False

    def get_pending_tasks(self):
        """Worker (Local VM) calls this to check for missions."""
        if not self.client: return []
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Tasks")
            all_tasks = ws.get_all_records()
            return [(idx + 2, task) for idx, task in enumerate(all_tasks) if task.get('Status') == 'PENDING']
        except Exception as e:
            print(f"❌ Error fetching tasks: {e}")
            return []

    def update_task_status(self, row_idx, status):
        """Updates the mission status for the Cloud UI."""
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Tasks")
            ws.update_cell(row_idx, 2, status)
        except: pass

    # --- 📊 BATCH LOGGING LOGIC ---
    def get_next_batch_id(self):
        if not self.client: return 1
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try:
                ws = sheet.worksheet("Batches")
            except:
                ws = sheet.add_worksheet(title="Batches", rows="1000", cols="10")
                headers = ["Batch no.", "Date Range", "Selected Pairs", "TimeFrame", "Strategy", "Strictness", "Trade count", "Batch PnL", "Profit Factor", "% Win Rate"]
                ws.append_row(headers)
                return 1
            ids = ws.col_values(1)
            return int(ids[-1]) + 1 if len(ids) > 1 else 1
        except: return 1

    def log_batch_meta(self, data):
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Batches")
            ws.append_row(data)
        except Exception as e: print(f"❌ Batch Meta Error: {e}")

    def create_batch_sheet(self, batch_id):
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            name = f"Batch_{batch_id}"
            try: sheet.worksheet(name)
            except:
                ws = sheet.add_worksheet(title=name, rows="1000", cols="16")
                ws.append_row(["Batch ID", "Strategy", "Pair", "Signal", "Time Open", "Entry Point", "SL Price", "SL Money", "Lot size", "Spreads", "TP Money", "TP Price", "Exit Point", "Time Closed", "PnL", "Close Reason"])
        except Exception as e: print(f"❌ Create Sheet Error: {e}")

    def log_batch_results(self, batch_id, data):
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet(f"Batch_{batch_id}")
            ws.append_rows(data)
        except Exception as e: print(f"❌ Results Error: {e}")

    def finalize_batch_stats(self, batch_id):
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws_batch = sheet.worksheet(f"Batch_{batch_id}")
            all_data = ws_batch.get_all_records()
            if not all_data: return
            
            total_trades = len(all_data)
            pnl_list = [float(row['PnL']) for row in all_data]
            total_pnl = sum(pnl_list)
            
            ws_main = sheet.worksheet("Batches")
            rows = ws_main.get_all_values()
            for idx, row in enumerate(rows):
                if row[0] == str(batch_id):
                    ws_main.update_cell(idx + 1, 7, total_trades)
                    ws_main.update_cell(idx + 1, 8, round(total_pnl, 2))
                    break
        except Exception as e: print(f"❌ Finalize Error: {e}")