#!/usr/bin/env python3
"""
Database Reset Script
Drops all existing tables and recreates them with correct schema
"""

import sys
import os
from sqlalchemy import text, MetaData
from database.connection import engine, SessionLocal
from database.models import Base

def reset_database():
    """Drop all tables and recreate them"""
    
    print("🔄 Resetting BDE Sales Portal Database...")
    print(f"📍 Database URL: {os.getenv('DATABASE_URL', 'default connection')}")
    
    try:
        # Drop all existing tables
        print("\n1️⃣ Dropping existing tables...")
        
        with engine.connect() as conn:
            # Get all table names
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """))
            
            existing_tables = [row[0] for row in result]
            
            if existing_tables:
                print(f"📋 Found {len(existing_tables)} existing tables:")
                for table in existing_tables:
                    print(f"   • {table}")
                
                # Drop all tables with CASCADE
                for table in existing_tables:
                    print(f"🗑️ Dropping table: {table}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    conn.commit()
            else:
                print("✅ No existing tables found")
        
        # Create all tables fresh
        print("\n2️⃣ Creating new tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Verify tables
        print("\n3️⃣ Verifying table creation...")
        with SessionLocal() as session:
            # Check each main table
            tables_to_check = [
                'customers', 
                'document_workflows', 
                'workflow_events', 
                'email_logs',
                'document_templates',
                'crm_contacts_cache',
                'crm_write_queue',
                'crm_bridge_audit_log'
            ]
            
            for table in tables_to_check:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"✅ {table}: {count} records")
                except Exception as e:
                    print(f"❌ {table}: {e}")
        
        print("\n🎉 Database reset complete!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    print("🏢 BDE Sales Document Portal - Database Reset")
    print("=" * 50)
    print("⚠️  WARNING: This will delete all existing data!")
    
    # For automation, skip confirmation
    response = "y"
    
    if response.lower() == 'y':
        success = reset_database()
        
        if success:
            print("\n✅ Database is ready!")
            print("Next step: Start the CRM bridge service")
        else:
            print("\n💥 Database reset failed!")
            sys.exit(1)
    else:
        print("Operation cancelled.")
        sys.exit(0)