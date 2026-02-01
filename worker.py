import time
from src.backtester import BacktestEngine
from src.cloud import CloudManager
from datetime import datetime
import streamlit as st # Only used for the progress bar Mock if needed

class DummyProgress:
    def progress(self, val): pass

def run_worker():
    """The Heavy Lifter 🏋️. Runs on the Windows VM with MT5."""
    print("🚀 Worker Online. Waiting for missions from Streamlit Cloud...")
    engine = BacktestEngine()
    cloud = CloudManager()
    
    while True:
        # 🕵️‍♂️ Check for PENDING missions
        tasks = cloud.get_pending_tasks()
        
        if not tasks:
            print("😴 No missions found. Chilling for 10s...")
            time.sleep(10)
            continue
            
        for row_idx, task in tasks:
            print(f"🎯 Mission Received: {task['Pairs']} on {task['TF']}")
            cloud.update_task_status(row_idx, "RUNNING")
            
            try:
                # 1. Startup MT5
                success, msg = engine.startup()
                if not success:
                    print(f"❌ MT5 Failed: {msg}")
                    cloud.update_task_status(row_idx, f"ERROR: {msg}")
                    continue
                
                # 2. Extract Task Details
                pairs = task['Pairs'].split(",")
                tf = task['TF']
                recipe = task['Recipe'].split("+")
                strictness = task['Strictness']
                start_dt = datetime.strptime(str(task['Start']), "%Y-%m-%d")
                end_dt = datetime.strptime(str(task['End']), "%Y-%m-%d")
                
                # 3. Execute
                batch_id = engine.init_batch(pairs, tf, recipe, strictness, start_dt, end_dt)
                
                for pair in pairs:
                    print(f"📈 Backtesting {pair}...")
                    engine.run_show(batch_id, pair, tf, start_dt, end_dt, recipe, strictness, DummyProgress())
                
                engine.finalize_show(batch_id)
                engine.shutdown()
                
                # 4. Success!
                cloud.update_task_status(row_idx, f"COMPLETED (Batch {batch_id})")
                print(f"✅ Mission Accomplished: Batch {batch_id}")
                
            except Exception as e:
                print(f"🔥 Critical Failure: {e}")
                cloud.update_task_status(row_idx, f"FAILED: {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    run_worker()