#!/usr/bin/env python3
"""
Database Setup Script
Creates all tables and tests the connection to Render PostgreSQL
"""

import sys
import os
from sqlalchemy import text
from database.connection import engine, SessionLocal, test_connection
from database.models import Base

def setup_database():
    """Create all database tables"""
    
    print("🔧 Setting up BDE Sales Portal Database...")
    print(f"📍 Database URL: {os.getenv('DATABASE_URL', 'default connection')}")
    
    try:
        # Test connection first
        print("\n1️⃣ Testing database connection...")
        connection_test = test_connection()
        
        if connection_test["status"] == "error":
            print(f"❌ Database connection failed: {connection_test['error']}")
            return False
        
        print("✅ Database connection successful!")
        
        # Create all tables
        print("\n2️⃣ Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Test with a simple query
        print("\n3️⃣ Testing table access...")
        with SessionLocal() as session:
            # Test customers table
            result = session.execute(text("SELECT COUNT(*) FROM customers"))
            customer_count = result.scalar()
            print(f"📊 Customers table: {customer_count} records")
            
            # Test CRM cache table
            result = session.execute(text("SELECT COUNT(*) FROM crm_contacts_cache"))
            crm_count = result.scalar()
            print(f"📊 CRM cache table: {crm_count} records")
            
            # Test workflow table
            result = session.execute(text("SELECT COUNT(*) FROM document_workflows"))
            workflow_count = result.scalar()
            print(f"📊 Document workflows table: {workflow_count} records")
        
        print("\n✅ Database setup complete!")
        print("🚀 Ready to start CRM bridge service")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def show_table_info():
    """Show information about created tables"""
    
    try:
        with SessionLocal() as session:
            # Get table names
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            
            print(f"\n📋 Created tables ({len(tables)}):")
            for table in tables:
                print(f"   ✓ {table}")
                
    except Exception as e:
        print(f"❌ Failed to get table info: {e}")

if __name__ == "__main__":
    print("🏢 BDE Sales Document Portal - Database Setup")
    print("=" * 50)
    
    success = setup_database()
    
    if success:
        show_table_info()
        print("\n🎉 Database is ready!")
        print("Next step: Start the CRM bridge service")
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)