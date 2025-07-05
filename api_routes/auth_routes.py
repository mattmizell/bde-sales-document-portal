"""
Authentication API Routes
Login, logout, user management endpoints
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database.connection import get_db_session
from services.auth_service import auth_service, get_current_user, require_admin, require_manager
from models.auth import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    user: dict
    token: str
    expires_at: str

class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "user"

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db_session)
):
    """User login endpoint"""
    
    # Authenticate user
    user = auth_service.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    session = auth_service.create_session(db, user, ip_address, user_agent)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session.raw_token,
        httponly=True,
        secure=True,  # Use HTTPS in production
        samesite="lax",
        max_age=3600 * 8  # 8 hours
    )
    
    return LoginResponse(
        success=True,
        user=user.to_dict(),
        token=session.raw_token,
        expires_at=session.expires_at.isoformat()
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """User logout endpoint"""
    
    # Get token from cookie or header
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if token:
        auth_service.logout_user(db, token)
    
    # Clear cookie
    response.delete_cookie("session_token")
    
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    
    return {
        "user": current_user.to_dict()
    }

@router.post("/users", dependencies=[Depends(require_admin())])
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new user (admin only)"""
    
    try:
        user = auth_service.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            created_by=current_user.username
        )
        
        return {
            "success": True,
            "user": user.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users", dependencies=[Depends(require_manager())])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """List all users (manager/admin only)"""
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    return {
        "users": [user.to_dict() for user in users],
        "total": db.query(User).count(),
        "skip": skip,
        "limit": limit
    }

@router.get("/users/{user_id}", dependencies=[Depends(require_manager())])
async def get_user(
    user_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID (manager/admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user": user.to_dict()
    }

@router.put("/users/{user_id}", dependencies=[Depends(require_admin())])
async def update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if update_data.first_name is not None:
        user.first_name = update_data.first_name
    if update_data.last_name is not None:
        user.last_name = update_data.last_name
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.is_active is not None:
        user.is_active = update_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "user": user.to_dict()
    }

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    
    # Verify current password
    if not current_user.check_password(password_data.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Set new password
    current_user.set_password(password_data.new_password)
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }

@router.delete("/users/{user_id}", dependencies=[Depends(require_admin())])
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete user (admin only)"""
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "User deactivated successfully"
    }

@router.post("/cleanup-sessions", dependencies=[Depends(require_admin())])
async def cleanup_sessions(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Clean up expired sessions (admin only)"""
    
    expired_count = auth_service.cleanup_expired_sessions(db)
    
    return {
        "success": True,
        "expired_sessions_cleaned": expired_count
    }