#!/usr/bin/env python
"""
RoadSentinel AI — MongoDB Atlas Database & Application Server
Entrypoint: server.py

Connects directly to MongoDB Atlas, seeds collections and indexes,
synchronizes historical inspection logs, and launches the FastAPI backend.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.database import mongo_manager
import inspection_store as istore
import uvicorn

def initialize_database():
    print("=" * 60)
    print("🛣️  RoadSentinel AI — Database & API Server")
    print("=" * 60)
    
    # 1. Verify MongoDB Connection
    if mongo_manager.is_connected():
        print(f"✅ [MongoDB Atlas] Connected to: {settings.MONGODB_DB_NAME}")
        col = mongo_manager.get_collection("inspections")
        
        # 2. Sync local JSON records to MongoDB
        local_records = istore.load_all_inspections()
        synced_count = 0
        if col is not None and local_records:
            for r in local_records:
                clean_r = istore._sanitize_for_json(r)
                col.update_one(
                    {"inspection_id": clean_r["inspection_id"]},
                    {"$set": clean_r},
                    upsert=True
                )
                synced_count += 1
            print(f"📦 [MongoDB Atlas] Synchronized {synced_count} inspection record(s) to cloud database.")

        # 3. Print collections and stats
        user_col = mongo_manager.get_collection("users")
        user_count = user_col.count_documents({}) if user_col is not None else 0
        order_col = mongo_manager.get_collection("work_orders")
        order_count = order_col.count_documents({}) if order_col is not None else 0
        print(f"👥 [Users & RBAC] {user_count} registered users (Citizen, Authority, Worker).")
        print(f"🛠️ [Work Orders] {order_count} repair assignments active.")
    else:
        print("⚠️ [MongoDB Atlas] Could not connect to Atlas. Operating in local JSON fallback mode.")

    print("-" * 60)
    print("🚀 [FastAPI REST API] Starting on http://127.0.0.1:8000")
    print("📚 [Interactive Swagger Docs] http://127.0.0.1:8000/docs")
    print("=" * 60)

if __name__ == "__main__":
    initialize_database()
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
