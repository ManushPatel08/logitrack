"""
Background worker that runs alongside FastAPI to ingest data periodically.
This is a lightweight alternative to running a separate worker service.
"""
import threading
import time
import os
import sys

# Add worker directory to path to import worker logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'worker'))

def run_worker_loop():
    """Run worker in a background thread."""
    # Import worker main function
    try:
        from worker import main as worker_main
        
        # Get interval from env
        if os.environ.get("USE_AIS_API", "false").lower() == "true":
            interval = int(os.environ.get("AISSTREAM_POLL_INTERVAL_SECONDS", "60"))
        else:
            interval = int(os.environ.get("MOCK_EVENT_INTERVAL_SECONDS", "5"))
        
        print(f"🔄 Background worker thread starting... (interval: {interval}s)")
        
        while True:
            try:
                worker_main()
                time.sleep(interval)
            except Exception as e:
                print(f"❌ Worker error: {e}")
                time.sleep(10)  # Wait before retry
                
    except ImportError as e:
        print(f"⚠️ Could not import worker module: {e}")
        print("⚠️ Worker functionality disabled. Deploy separate worker service for data ingestion.")

def start_background_worker():
    """Start worker in background thread."""
    # Only start if environment variable is set
    if os.environ.get("ENABLE_BACKGROUND_WORKER", "false").lower() == "true":
        worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
        worker_thread.start()
        print("✅ Background worker thread started")
    else:
        print("ℹ️ Background worker disabled. Set ENABLE_BACKGROUND_WORKER=true to enable.")
