#!/usr/bin/env python3
"""
Test script to verify local setup
"""

import os
import sys

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    
    try:
        from database.connection import get_db_session, engine
        print("✅ Database imports OK")
    except Exception as e:
        print(f"❌ Database import error: {e}")
        return False
    
    try:
        from models.auth import User, UserSession
        from models.core import Customer, DocumentTemplate, DocumentWorkflow
        print("✅ Model imports OK")
    except Exception as e:
        print(f"❌ Model import error: {e}")
        return False
    
    try:
        from services.auth_service import auth_service
        from services.docuseal_service import DocuSealService
        print("✅ Service imports OK")
    except Exception as e:
        print(f"❌ Service import error: {e}")
        return False
    
    try:
        from api_routes.auth_routes import router as auth_router
        from api_routes.customer_routes import router as customer_router
        from api_routes.workflow_routes import router as workflow_router
        print("✅ Route imports OK")
    except Exception as e:
        print(f"❌ Route import error: {e}")
        return False
    
    return True

def test_environment():
    """Test environment variables"""
    print("\nTesting environment...")
    
    required_vars = [
        "DATABASE_URL",
        "DOCUSEAL_SERVICE_URL", 
        "DOCUSEAL_API_TOKEN"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Please check your .env file")
        return False
    else:
        print("✅ All required environment variables present")
        return True

def test_database():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from database.connection import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== BDE Sales Document Portal - Local Test ===\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    tests = [
        test_imports(),
        test_environment(),
        test_database()
    ]
    
    if all(tests):
        print("\n✅ All tests passed! Ready to run the portal.")
        print("\nTo start the portal, run:")
        print("  python main_portal.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()