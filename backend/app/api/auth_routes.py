from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.schemas import UserProfile, GoogleAuthRequest, LocalLoginRequest
from backend.app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & Roles"])

@router.post("/google", response_model=UserProfile)
async def google_oauth_login(payload: GoogleAuthRequest):
    """
    Authenticates user via Google OAuth credential / profile.
    Automatically provisions or updates user in MongoDB Atlas.
    """
    if not payload.email or "@" not in payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email address is required for Google OAuth."
        )
    return auth_service.google_auth(payload)

@router.post("/login", response_model=UserProfile)
async def local_role_login(payload: LocalLoginRequest):
    """
    Local / Demo login with role switching (Citizen, Authority, Worker).
    Stores profile into MongoDB and returns active role profile.
    """
    if not payload.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
    return auth_service.local_login(email=payload.email, role=payload.role)

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(email: str = Query("citizen@roadsentinel.ai")):
    """Retrieves authenticated user profile from MongoDB."""
    user = auth_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/users", response_model=List[UserProfile])
async def list_users_by_role(role: Optional[str] = Query(None, description="Filter users by role: citizen, authority, worker")):
    """Lists registered users, useful for dispatching tasks to field workers."""
    return auth_service.list_users(role=role)
