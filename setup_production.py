#!/usr/bin/env python3
"""
Production Setup Script
Run this after first deployment to setup database tables
"""

import os
import sys
import logging
from database.connection import create_tables, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_production():
    """Setup production environment"""
    
    logger.info("🚀 Setting up BDE Sales Document Portal production environment...")
    
    # Test database connection
    logger.info("📊 Testing database connection...")
    db_test = test_connection()
    
    if db_test["status"] != "healthy":
        logger.error(f"❌ Database connection failed: {db_test.get('error')}")
        sys.exit(1)
    
    logger.info("✅ Database connection successful")
    
    # Create tables
    logger.info("🔨 Creating database tables...")
    try:
        create_tables()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        sys.exit(1)
    
    logger.info("🎉 Production setup complete!")
    logger.info("📋 Next steps:")
    logger.info("  1. Sync CRM data: python sync_crm_full.py")
    logger.info("  2. Test API endpoints at /docs")

if __name__ == "__main__":
    setup_production()