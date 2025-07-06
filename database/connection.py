"""
Database Connection Management
Clean PostgreSQL connection for BDE Sales Document Portal
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database URL from environment (Render will set this automatically)
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    # Fallback for local development only
    'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create declarative base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

def get_db_session() -> Generator:
    """Get database session with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Get database session in context manager"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database context error: {e}")
        raise
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

def test_connection():
    """Test database connection"""
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "error", "error": str(e)}