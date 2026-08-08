
import time
import json
import logging
import requests
import os
from datetime import datetime

# Note: In a real app we'd copy the platform-specific get_active_window here,
# but for the hackathon we can safely import it from the module.
from modules.screen_tracker.tracker import get_active_window
from modules.screen_tracker.categorizer import categorize_app

logging.basicConfig(level=logging.INFO)
print("Starting Mimo Standalone Desktop Tracker...")

CACHE_FILE = "mimo_cache.json"
CLOUD_URL = os.getenv("MIMO_CLOUD_URL", "http://localhost:8000")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def sync_cache():
    cache = load_cache()
    if not cache:
        return
    
    try:
        # Mock push - normally we'd push to /sync/push
        for event in list(cache):
            requests.post(f"{CLOUD_URL}/screen/mock", json=event, timeout=2)
            cache.remove(event)
        save_cache(cache)
        logging.info("Synced offline cache with cloud.")
    except Exception as e:
        logging.warning(f"Offline mode. Could not sync: {e}")
        save_cache(cache)

try:
    while True:
        app, title = get_active_window()
        category = categorize_app(app, title)
        
        event = {
            "app": app,
            "title": title[:80],
            "category": category,
            "ts": datetime.now().isoformat()
        }
        
        # Add to cache and try to sync
        cache = load_cache()
        cache.append(event)
        save_cache(cache)
        
        sync_cache()
        
        time.sleep(2)
except KeyboardInterrupt:
    print("Tracker stopped.")
