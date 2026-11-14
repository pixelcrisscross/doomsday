import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from backend.app.core.config import settings

logger = logging.getLogger("roadsentinel.db")

class MongoManager:
    _instance: Optional["MongoManager"] = None
    client: Optional[pymongo.MongoClient] = None
    db: Optional[Database] = None
    _is_connected: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoManager, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            uri = settings.MONGODB_URI
            db_name = settings.MONGODB_DB_NAME
            logger.info(f"Connecting to MongoDB Atlas database: {db_name}...")
            self.client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=50
            )
            # Test connection
            self.client.admin.command("ping")
            self.db = self.client[db_name]
            self._is_connected = True
            logger.info("Successfully established connection to MongoDB Atlas!")
            self._init_collections_and_indexes()
            self._seed_default_users()
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}. Running in local storage fallback mode.")
            self._is_connected = False
            self.db = None

    def is_connected(self) -> bool:
        if not self._is_connected or self.client is None:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            self._is_connected = False
            return False

    def get_collection(self, name: str) -> Optional[Collection]:
        if self.db is not None and self._is_connected:
            return self.db[name]
        return None

    def _init_collections_and_indexes(self):
        if self.db is None:
            return
        try:
            # Inspections collection
            inspections = self.db["inspections"]
            inspections.create_index("inspection_id", unique=True)
            inspections.create_index([("latitude", pymongo.ASCENDING), ("longitude", pymongo.ASCENDING)])
            inspections.create_index("verification.status")
            inspections.create_index("repair_status")
            inspections.create_index("created_by")

            # Users collection
            users = self.db["users"]
            users.create_index("email", unique=True)
            users.create_index("role")
            users.create_index("google_id", sparse=True)

            # Work Orders collection
            work_orders = self.db["work_orders"]
            work_orders.create_index("order_id", unique=True)
            work_orders.create_index("inspection_id")
            work_orders.create_index("assigned_worker_id")
            work_orders.create_index("status")

            # Repair Logs collection
            repair_logs = self.db["repair_logs"]
            repair_logs.create_index("inspection_id")
            repair_logs.create_index("timestamp")
        except Exception as e:
            logger.warning(f"Failed to create some MongoDB indexes: {e}")

    def _seed_default_users(self):
        if self.db is None:
            return
        users = self.db["users"]
        default_users = [
            {
                "email": "citizen@roadsentinel.ai",
                "name": "Citizen Reporter",
                "role": "citizen",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=citizen",
                "provider": "local",
                "active": True,
                "created_at": datetime.now().isoformat(),
                "bio": "Civic road safety contributor"
            },
            {
                "email": "authority@roadsentinel.ai",
                "name": "Municipal Officer (Validator)",
                "role": "authority",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=authority",
                "provider": "local",
                "active": True,
                "department": "Public Works & Transportation",
                "created_at": datetime.now().isoformat(),
                "bio": "Municipal damage validation officer & work dispatcher"
            },
            {
                "email": "worker@roadsentinel.ai",
                "name": "Field Repair Contractor",
                "role": "worker",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=worker",
                "provider": "local",
                "active": True,
                "skills": ["Hot Asphalt Paving", "Cold Patching", "Compaction"],
                "created_at": datetime.now().isoformat(),
                "bio": "Asphalt repair & pothole remediation specialist"
            }
        ]
        for u in default_users:
            users.update_one({"email": u["email"]}, {"$setOnInsert": u}, upsert=True)

mongo_manager = MongoManager()

def get_database() -> Optional[Database]:
    return mongo_manager.db
