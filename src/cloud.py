import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_DICT, SHEET_URL, USER_DEFAULT_MARKETS
from datetime import datetime

class CloudManager:
    """The Chief Aesthetic Officer 🎨. Handles communication between UI and Ground Worker."""
    def __init__(self):
        self.client = None
        self.authenticated = False
        self.setup()

    def setup(self):
        """Initializes the link to the Motherboard."""
        if not GOOGLE_CREDS_DICT or "client_email" not in GOOGLE_CREDS_DICT:
            print("⚠️ Cloud Manager standing by: Missing Credentials in config.")
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
            # Try a test connection to verify auth immediately
            self.client.open_by_url(SHEET_URL)
            self.authenticated = True
            print("🛰️ Cloud C2 Link Established. We are SO back.")
        except Exception as e:
            print(f"❌ Cloud Setup Failed: {e}")
            self.authenticated = False

    def _set_dropdown_request(self, sheet_id, start_row, end_row, start_col, end_col, options):
        """Helper to create a data validation request for the Google Sheets API."""
        return {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": opt} for opt in options]
                    },
                    "showCustomUi": True
                }
            }
        }

    # --- 🛰️ MISSION CONTROL (Streamlit Side) ---
    def request_task(self, pairs, tf, recipe, strictness, start_date, end_date):
        """Drops a mission into the 'Tasks' sheet for the local worker to grab."""
        if not self.authenticated: 
            print("❌ Cannot request task: CloudManager not authenticated.")
            return False
            
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try:
                ws = sheet.worksheet("Tasks")
            except Exception:
                # If Tasks doesn't exist, create it with headers
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
            # This will show up in your Streamlit/Worker logs
            print(f"❌ Mission Request Error: {e}")
            if "PERMISSION_DENIED" in str(e):
                print("💡 Pro Tip: Did you share the sheet with your service account email?")
            return False

    # --- 🚜 GROUND WORKER LOGIC (Worker Side) ---
    def get_pending_tasks(self):
        """Worker checks if the Commander has sent any new orders."""
        if not self.authenticated: return []
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Tasks")
            all_tasks = ws.get_all_records()
            return [(idx + 2, task) for idx, task in enumerate(all_tasks) if task.get('Status') == 'PENDING']
        except Exception as e:
            print(f"⚠️ Worker polling error: {e}")
            return []

    def update_task_status(self, row_idx, status):
        """Worker updates the status (RUNNING, COMPLETED, ERROR)."""
        if not self.authenticated: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Tasks")
            ws.update_cell(row_idx, 2, status)
        except Exception as e: 
            print(f"⚠️ Status update failed: {e}")

    # --- 📊 TACTICAL LOGGING (The Sauce) ---
    def get_next_batch_id(self):
        if not self.authenticated: return 1
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try:
                ws = sheet.worksheet("Batches")
            except:
                ws = sheet.add_worksheet(title="Batches", rows="1000", cols="10")
                headers = ["Batch no.", "Date Range", "Selected Pairs", "TimeFrame", "Strategy", "Strictness", "Trade count", "Batch PnL", "Profit Factor", "% Win Rate"]
                ws.append_row(headers)
                ws.format('A1:J1', {'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}, 'backgroundColor': {'red': 0.1, 'green': 0.35, 'blue': 0.25}, 'horizontalAlignment': 'CENTER'})
                ws.freeze(rows=1)
                return 1
            ids = ws.col_values(1)
            return int(ids[-1]) + 1 if len(ids) > 1 else 1
        except: return 1

    def log_batch_meta(self, data):
        """Logs the strategy setup into the master 'Batches' sheet."""
        if not self.authenticated: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Batches")
            ws.append_row(data)
            row_idx = len(ws.get_all_values())
            ws.format(f'A{row_idx}:J{row_idx}', {'borders': {'top': {'style': 'SOLID'}, 'bottom': {'style': 'SOLID'}, 'left': {'style': 'SOLID'}, 'right': {'style': 'SOLID'}}, 'horizontalAlignment': 'CENTER'})
            # Add dropdown for strictness
            requests = [self._set_dropdown_request(ws.id, row_idx - 1, row_idx, 5, 6, ['Low', 'Medium', 'High'])]
            sheet.batch_update({"requests": requests})
        except Exception as e: print(f"❌ Batch Meta Error: {e}")

    def create_batch_sheet(self, batch_id):
        """Creates a dedicated tab for the individual trades of a mission."""
        if not self.authenticated: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            name = f"Batch_{batch_id}"
            try: sheet.worksheet(name)
            except:
                ws = sheet.add_worksheet(title=name, rows="1000", cols="16")
                ws.append_row(["Batch ID", "Strategy", "Pair", "Signal", "Time Open", "Entry Point", "SL Price", "SL Money", "Lot size", "Spreads", "TP Money", "TP Price", "Exit Point", "Time Closed", "PnL", "Close Reason"])
                ws.freeze(rows=1)
                ws.format('A1:P1', {'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}, 'backgroundColor': {'red': 0.1, 'green': 0.35, 'blue': 0.25}})
                
                # Dynamic Green/Red formatting for PnL column (O)
                requests = [
                    {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 14, "endColumnIndex": 15}], "booleanRule": {"condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]}, "format": {"backgroundColor": {"green": 0.8, "red": 0.4, "blue": 0.4}}}}, "index": 0}},
                    {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 14, "endColumnIndex": 15}], "booleanRule": {"condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]}, "format": {"backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.4}}}}, "index": 1}}
                ]
                sheet.batch_update({"requests": requests})
        except Exception as e: print(f"❌ Create Sheet Error: {e}")

    def log_batch_results(self, batch_id, data):
        """Streams trade results into the batch tab."""
        if not self.authenticated: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet(f"Batch_{batch_id}")
            start_row = len(ws.get_all_values()) + 1
            ws.append_rows(data)
            end_row = start_row + len(data) - 1
            ws.format(f'A{start_row}:P{end_row}', {'borders': {'top': {'style': 'SOLID'}, 'bottom': {'style': 'SOLID'}, 'left': {'style': 'SOLID'}, 'right': {'style': 'SOLID'}}})
        except Exception as e: print(f"❌ Results Log Error: {e}")

    def finalize_batch_stats(self, batch_id):
        """The Heavy Lifter. Calculates Win Rate, PF, and PnL and updates 'Batches' sheet."""
        if not self.authenticated: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws_batch = sheet.worksheet(f"Batch_{batch_id}")
            all_data = ws_batch.get_all_records()
            if not all_data: return
            
            total_trades = len(all_data)
            pnl_list = [float(row['PnL']) for row in all_data]
            total_pnl = sum(pnl_list)
            
            profits = [p for p in pnl_list if p > 0]
            losses = [abs(l) for l in pnl_list if l < 0]
            
            win_rate = (len(profits) / total_trades * 100) if total_trades > 0 else 0
            pf = (sum(profits) / sum(losses)) if sum(losses) > 0 else (sum(profits) if profits else 1.0)
            
            # Add footer stats to the batch tab
            ws_batch.append_row([])
            ws_batch.append_row(["COUNT:", total_trades])
            ws_batch.append_row(["GROSS PNL:", round(total_pnl, 2)])
            ws_batch.append_row(["WIN RATE:", f"{round(win_rate, 2)}%"])
            ws_batch.append_row(["PROFIT FACTOR:", round(pf, 2)])
            
            # Update the Master 'Batches' sheet
            ws_main = sheet.worksheet("Batches")
            rows = ws_main.get_all_values()
            for idx, row in enumerate(rows):
                if row[0] == str(batch_id):
                    ws_main.update_cell(idx + 1, 7, total_trades) # Count
                    ws_main.update_cell(idx + 1, 8, round(total_pnl, 2)) # PnL
                    ws_main.update_cell(idx + 1, 9, round(pf, 2)) # PF
                    ws_main.update_cell(idx + 1, 10, f"{round(win_rate, 1)}%") # Win Rate
                    break
        except Exception as e: print(f"❌ Finalize Stats Error: {e}")