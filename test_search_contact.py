#!/usr/bin/env python3
"""
Test searching for the Gas O Matt contact in the database
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Use DATABASE_URL from .env file
DATABASE_URL = 'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def search_test_contact():
    """Search for Gas O Matt contact"""
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Search for Gas O Matt
                cur.execute("""
                    SELECT contact_id, name, first_name, last_name, 
                           company_name, email, phone, address, 
                           created_at, last_sync
                    FROM crm_contacts_cache 
                    WHERE company_name ILIKE %s 
                       OR email = %s
                       OR name ILIKE %s
                    ORDER BY name
                """, ("%Gas O Matt%", "matt.mizell@gmail.com", "%Matt%"))
                
                rows = cur.fetchall()
                
                print(f"🔍 Found {len(rows)} matching contacts:")
                for row in rows:
                    print(f"  • ID: {row['contact_id']}")
                    print(f"    Name: {row['name']}")
                    print(f"    Company: {row['company_name']}")
                    print(f"    Email: {row['email']}")
                    print(f"    Phone: {row['phone']}")
                    print(f"    Address: {row['address']}")
                    print(f"    Created: {row['created_at']}")
                    print("")
                
                return len(rows) > 0
                
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Searching for Gas O Matt test contact")
    print("=" * 50)
    
    found = search_test_contact()
    
    if found:
        print("✅ Test contact found in database!")
    else:
        print("❌ Test contact not found")