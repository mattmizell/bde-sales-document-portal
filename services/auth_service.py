"""
Authentication Service
Handles user login, logout, session management, and authorization
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.auth import User, UserSession
from database.connection import get_db_session

# Security configuration
SESSION_EXPIRE_HOURS = 8
TOKEN_LENGTH = 32

class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    def create_user(
        self, 
        db: Session,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "user",
        created_by: str = None
    ) -> User:
        """Create new user account"""
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username or email already exists"
            )
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            created_by=created_by
        )
        user.set_password(password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def authenticate_user(
        self, 
        db: Session, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user with username/password"""
        
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.is_active or not user.check_password(password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    def create_session(
        self,
        db: Session,
        user: User,
        ip_address: str = None,
        user_agent: str = None
    ) -> UserSession:
        """Create user session with token"""
        
        # Generate secure session token
        token = secrets.token_urlsafe(TOKEN_LENGTH)
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            session_token=self._hash_token(token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Return token in session object for convenience
        session.raw_token = token
        return session
    
    def get_user_from_token(
        self,
        db: Session,
        token: str
    ) -> Optional[User]:
        """Get user from session token"""
        
        if not token:
            return None
        
        # Hash token for lookup
        token_hash = self._hash_token(token)
        
        # Find active session
        session = db.query(UserSession).filter(
            UserSession.session_token == token_hash,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            return None
        
        # Get user
        user = db.query(User).filter(
            User.id == session.user_id,
            User.is_active == True
        ).first()
        
        return user
    
    def logout_user(self, db: Session, token: str) -> bool:
        """Logout user by deactivating session"""
        
        if not token:
            return False
        
        token_hash = self._hash_token(token)
        
        session = db.query(UserSession).filter(
            UserSession.session_token == token_hash,
            UserSession.is_active == True
        ).first()
        
        if session:
            session.is_active = False
            db.commit()
            return True
        
        return False
    
    def require_auth(
        self,
        request: Request,
        db: Session = Depends(get_db_session),
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> User:
        """Dependency to require authentication"""
        
        token = None
        
        # Try to get token from Authorization header
        if credentials:
            token = credentials.credentials
        
        # Try to get token from cookie
        if not token:
            token = request.cookies.get("session_token")
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        user = self.get_user_from_token(db, token)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            )
        
        return user
    
    def require_permission(self, permission: str):
        """Dependency factory to require specific permission"""
        
        def permission_checker(
            user: User = Depends(self.require_auth)
        ) -> User:
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required"
                )
            return user
        
        return permission_checker
    
    def require_role(self, required_role: str):
        """Dependency factory to require specific role"""
        
        def role_checker(
            user: User = Depends(self.require_auth)
        ) -> User:
            if user.role != required_role:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{required_role}' required"
                )
            return user
        
        return role_checker
    
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def cleanup_expired_sessions(self, db: Session) -> int:
        """Clean up expired sessions"""
        
        expired_count = db.query(UserSession).filter(
            UserSession.expires_at <= datetime.utcnow()
        ).update({"is_active": False})
        
        db.commit()
        return expired_count

# Global auth service instance
auth_service = AuthService()

# Convenience functions for use in routes
def get_current_user(
    request: Request,
    db: Session = Depends(get_db_session)
) -> User:
    """Get current authenticated user"""
    return auth_service.require_auth(request, db)

def require_admin():
    """Require admin role"""
    return auth_service.require_role("admin")

def require_manager():
    """Require manager or admin role"""
    def manager_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in ["admin", "manager"]:
            raise HTTPException(status_code=403, detail="Manager role required")
        return user
    return manager_checker