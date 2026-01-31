import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_DICT, SHEET_URL, USER_DEFAULT_MARKETS

class CloudManager:
    """The Chief Aesthetic Officer 🎨. Handles logging, formatting, and making sure the pips look pretty."""
    def __init__(self):
        self.client = None
        self.setup()

    def setup(self):
        try:
            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT, 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            self.client = gspread.authorize(creds)
        except Exception as e:
            print(f"❌ Cloud Setup Failed: {e}")

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

    def get_next_batch_id(self):
        if not self.client: return 1
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try:
                ws = sheet.worksheet("Batches")
            except:
                # 🛠️ Updated to 10 columns for 'Trade count'
                ws = sheet.add_worksheet(title="Batches", rows="1000", cols="10")
                headers = [
                    "Batch no.", "Date Range", "Selected Pairs", "TimeFrame", 
                    "Strategy", "Strictness", "Trade count", "Batch PnL", "Profit Factor", "% Win Rate"
                ]
                ws.append_row(headers)
                
                # 💅 Styling the header (A to J)
                ws.format('A1:J1', {
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}},
                    'backgroundColor': {'red': 0.1, 'green': 0.35, 'blue': 0.25},
                    'horizontalAlignment': 'CENTER'
                })
                ws.freeze(rows=1)
                return 1
            ids = ws.col_values(1)
            return int(ids[-1]) + 1 if len(ids) > 1 else 1
        except: return 1

    def log_batch_meta(self, data):
        """Logs initial calibrations and adds dropdowns via batch_update."""
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet("Batches")
            ws.append_row(data)
            
            row_idx = len(ws.get_all_values())
            
            # 🎨 Border formatting (A to J)
            ws.format(f'A{row_idx}:J{row_idx}', {
                'borders': {
                    'top': {'style': 'SOLID'}, 'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'}, 'right': {'style': 'SOLID'}
                },
                'horizontalAlignment': 'CENTER'
            })

            # 🔥 Dropdown for Strictness (Column F / Index 5)
            requests = [
                self._set_dropdown_request(ws.id, row_idx - 1, row_idx, 5, 6, ['Low', 'Medium', 'High'])
            ]
            sheet.batch_update({"requests": requests})
            
        except Exception as e:
            print(f"❌ Batch Metadata Logging Failed: {e}")

    def create_batch_sheet(self, batch_id):
        """Creates a dedicated worksheet with table styling."""
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            name = f"Batch_{batch_id}"
            try:
                sheet.worksheet(name)
            except:
                headers = [
                    "Batch ID", "Strategy", "Pair", "Signal", "Time Open", 
                    "Entry Point", "SL Price", "SL Money", "Lot size", 
                    "Spreads", "TP Money", "TP Price", "Exit Point", 
                    "Time Closed", "PnL", "Close Reason"
                ]
                ws = sheet.add_worksheet(title=name, rows="1000", cols="16")
                ws.append_row(headers)
                
                ws.freeze(rows=1)
                ws.format('A1:P1', {
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}},
                    'backgroundColor': {'red': 0.1, 'green': 0.35, 'blue': 0.25}
                })

                requests = [
                    {
                        "addConditionalFormatRule": {
                            "rule": {
                                "ranges": [{"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 14, "endColumnIndex": 15}],
                                "booleanRule": {
                                    "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                                    "format": {"backgroundColor": {"green": 0.8, "red": 0.4, "blue": 0.4}}
                                }
                            }, "index": 0
                        }
                    },
                    {
                        "addConditionalFormatRule": {
                            "rule": {
                                "ranges": [{"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 14, "endColumnIndex": 15}],
                                "booleanRule": {
                                    "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                                    "format": {"backgroundColor": {"red": 0.8, "green": 0.4, "blue": 0.4}}
                                }
                            }, "index": 1
                        }
                    }
                ]
                sheet.batch_update({"requests": requests})
        except Exception as e:
            print(f"⚠️ Could not create formatted Batch_{batch_id} sheet: {e}")

    def log_batch_results(self, batch_id, data):
        """Logs simulation results and applies dropdowns using optimized batch requests."""
        if not self.client: return
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet(f"Batch_{batch_id}")
            start_row = len(ws.get_all_values()) + 1
            ws.append_rows(data)
            
            num_rows = len(data)
            end_row = start_row + num_rows - 1
            
            ws.format(f'A{start_row}:P{end_row}', {
                'borders': {
                    'top': {'style': 'SOLID'}, 'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'}, 'right': {'style': 'SOLID'}
                }
            })
            
            requests = []
            # Pair Dropdown (Column C / Index 2)
            requests.append(self._set_dropdown_request(ws.id, start_row - 1, end_row, 2, 3, USER_DEFAULT_MARKETS))
            # Close Reason Dropdown (Column P / Index 15)
            requests.append(self._set_dropdown_request(ws.id, start_row - 1, end_row, 15, 16, ['SL Hit', 'TP Hit', 'Data Ended']))
            
            sheet.batch_update({"requests": requests})
            
        except Exception as e:
            print(f"❌ Batch Results Logging Failed: {e}")

    def finalize_batch_stats(self, batch_id):
        """Updates the main table and appends summary info to Column A of the batch sheet."""
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws_batch = sheet.worksheet(f"Batch_{batch_id}")
            all_data = ws_batch.get_all_records()
            
            if not all_data: return

            total_trades = len(all_data)
            total_pnl = sum(float(row['PnL']) for row in all_data)
            profits = [float(row['PnL']) for row in all_data if float(row['PnL']) > 0]
            losses = [abs(float(row['PnL'])) for row in all_data if float(row['PnL']) < 0]
            
            win_rate = (len(profits) / total_trades * 100) if total_trades > 0 else 0
            pf = (sum(profits) / sum(losses)) if sum(losses) > 0 else (sum(profits) if profits else 1.0)

            # 🦶 Summary math moved to Column A for that clean vibe
            ws_batch.append_row([])
            ws_batch.append_row(["COUNT:", total_trades])
            ws_batch.append_row(["GROSS PNL:", round(total_pnl, 2)])

            # 📈 Update Main Table
            # G (7): Trade count | H (8): Batch PnL | I (9): Profit Factor | J (10): % Win Rate
            ws_main = sheet.worksheet("Batches")
            rows = ws_main.get_all_values()
            for idx, row in enumerate(rows):
                if row[0] == str(batch_id):
                    ws_main.update_cell(idx + 1, 7, total_trades)
                    ws_main.update_cell(idx + 1, 8, round(total_pnl, 2))
                    ws_main.update_cell(idx + 1, 9, round(pf, 2))
                    ws_main.update_cell(idx + 1, 10, f"{round(win_rate, 1)}%")
                    break

        except Exception as e:
            print(f"❌ Finalize Stats Failed: {e}")