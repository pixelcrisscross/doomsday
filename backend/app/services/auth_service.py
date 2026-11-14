import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.app.core.database import mongo_manager
from backend.app.schemas.schemas import UserProfile, GoogleAuthRequest

logger = logging.getLogger("roadsentinel.auth")

DEFAULT_USERS = [
    {
        "id": "USR-CITIZEN-01",
        "email": "citizen@roadsentinel.ai",
        "name": "Citizen Reporter",
        "role": "citizen",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=citizen",
        "provider": "local",
        "bio": "Civic road safety reporter",
        "created_at": "2026-11-14T00:00:00"
    },
    {
        "id": "USR-AUTHORITY-01",
        "email": "authority@roadsentinel.ai",
        "name": "Municipal Officer (Validator)",
        "role": "authority",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=authority",
        "provider": "local",
        "department": "Public Works & Urban Roads",
        "bio": "Municipal validation officer and field work dispatcher",
        "created_at": "2026-11-14T00:00:00"
    },
    {
        "id": "USR-WORKER-01",
        "email": "worker@roadsentinel.ai",
        "name": "Field Repair Contractor",
        "role": "worker",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=worker",
        "provider": "local",
        "skills": ["Hot Mix Asphalt", "Cold Patching", "Pothole Milling & Compaction"],
        "bio": "Certified road asphalt remediation technician",
        "created_at": "2026-11-14T00:00:00"
    }
]

class AuthService:
    def __init__(self):
        self._local_users: Dict[str, Dict[str, Any]] = {u["email"]: dict(u) for u in DEFAULT_USERS}

    def google_auth(self, req: GoogleAuthRequest) -> UserProfile:
        email = req.email.lower().strip()
        name = req.name.strip() or email.split("@")[0].title()
        avatar = req.avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
        role = req.role or "citizen"

        user_doc = {
            "email": email,
            "name": name,
            "avatar": avatar,
            "role": role,
            "provider": "google",
            "google_id": req.google_id,
            "last_login": datetime.now().isoformat()
        }

        col = mongo_manager.get_collection("users")
        if col is not None:
            try:
                col.update_one(
                    {"email": email},
                    {
                        "$set": user_doc,
                        "$setOnInsert": {"created_at": datetime.now().isoformat()}
                    },
                    upsert=True
                )
                db_user = col.find_one({"email": email})
                if db_user:
                    db_user["id"] = str(db_user.get("_id", email))
                    return UserProfile(**db_user)
            except Exception as e:
                logger.warning(f"Failed to upsert Google user into MongoDB: {e}")

        # Local in-memory fallback
        if email not in self._local_users:
            user_doc["id"] = f"USR-{len(self._local_users)+1:03d}"
            user_doc["created_at"] = datetime.now().isoformat()
            self._local_users[email] = user_doc
        else:
            self._local_users[email].update(user_doc)
        return UserProfile(**self._local_users[email])

    def local_login(self, email: str, role: Optional[str] = None) -> UserProfile:
        email = email.lower().strip()
        col = mongo_manager.get_collection("users")
        if col is not None:
            try:
                db_user = col.find_one({"email": email})
                if db_user:
                    if role and db_user.get("role") != role:
                        col.update_one({"email": email}, {"$set": {"role": role}})
                        db_user["role"] = role
                    db_user["id"] = str(db_user.get("_id", email))
                    return UserProfile(**db_user)
                else:
                    # Create new user in MongoDB
                    new_user = {
                        "email": email,
                        "name": email.split("@")[0].replace(".", " ").title(),
                        "role": role or "citizen",
                        "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
                        "provider": "local",
                        "created_at": datetime.now().isoformat(),
                        "last_login": datetime.now().isoformat()
                    }
                    res = col.insert_one(new_user)
                    new_user["id"] = str(res.inserted_id)
                    return UserProfile(**new_user)
            except Exception as e:
                logger.warning(f"MongoDB local login query failed: {e}")

        # Fallback to local
        if email in self._local_users:
            if role:
                self._local_users[email]["role"] = role
            return UserProfile(**self._local_users[email])
        
        new_user = {
            "id": f"USR-{len(self._local_users)+1:03d}",
            "email": email,
            "name": email.split("@")[0].replace(".", " ").title(),
            "role": role or "citizen",
            "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={email}",
            "provider": "local",
            "created_at": datetime.now().isoformat()
        }
        self._local_users[email] = new_user
        return UserProfile(**new_user)

    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        email = email.lower().strip()
        col = mongo_manager.get_collection("users")
        if col is not None:
            try:
                db_user = col.find_one({"email": email})
                if db_user:
                    db_user["id"] = str(db_user.get("_id", email))
                    return UserProfile(**db_user)
            except Exception:
                pass
        if email in self._local_users:
            return UserProfile(**self._local_users[email])
        return None

    def list_users(self, role: Optional[str] = None) -> List[UserProfile]:
        results: List[UserProfile] = []
        col = mongo_manager.get_collection("users")
        if col is not None:
            try:
                query = {"role": role} if role else {}
                for u in col.find(query):
                    u["id"] = str(u.get("_id", u["email"]))
                    results.append(UserProfile(**u))
                if results:
                    return results
            except Exception:
                pass
        
        for u in self._local_users.values():
            if not role or u.get("role") == role:
                results.append(UserProfile(**u))
        return results

auth_service = AuthService()
