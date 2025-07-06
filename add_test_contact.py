#!/usr/bin/env python3
"""
Add test contact "Gas O' Matt" directly to the database
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL from .env file
DATABASE_URL = 'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def add_test_contact():
    """Add Gas O' Matt test contact"""
    
    # Test contact data
    contact_data = {
        "contact_id": "test_gasomatt_001",
        "name": "Matt Mizell",
        "first_name": "Matt", 
        "last_name": "Mizell",
        "company_name": "Gas O'Matt",
        "email": "matt.mizell@gmail.com",
        "phone": "(618) 555-0123",
        "address": "1234 Highway 50 East, Mascoutah, IL 62258",
        "custom_fields": {
            "DBA": "Gas O'Matt Convenience Store",
            "FederalTaxID": "12-3456789",
            "StateTaxID": "IL-987654321", 
            "YearsInBusiness": "8",
            "NumberOfEmployees": "12",
            "AnnualDieselVolume": "180000",
            "AnnualGasolineVolume": "450000",
            "CreditAmountRequested": "75000",
            "EntityType": "LLC",
            "PurchasingManagerName": "Matt Mizell",
            "AccountsPayableName": "Sarah Johnson",
            "PurchasingEmail": "matt.mizell@gmail.com",
            "PurchasingPhone": "(618) 555-0123",
            "AccountsPayableEmail": "accounting@gasomatt.com",
            "AccountsPayablePhone": "(618) 555-0124",
            "FaxNumber": "(618) 555-0125",
            "BankName": "First National Bank of Mascoutah",
            "BankAddress": "500 Main Street",
            "BankCity": "Mascoutah",
            "BankState": "IL", 
            "BankZip": "62258",
            "BankPhone": "(618) 566-2000",
            "BankFax": "(618) 566-2001",
            "RoutingNumber": "071000013",
            "NameAtBank": "Gas O'Matt LLC",
            "BankContact": "Jennifer Smith",
            "ContractTerm": "10",
            "SiteIncentiveValue": "$65000",
            "PerformanceIncentiveValue": "$45000",
            "MarketingSupportValue": "$15000"
        }
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if contact already exists
                cur.execute("SELECT contact_id FROM crm_contacts_cache WHERE email = %s", 
                           (contact_data["email"],))
                existing = cur.fetchone()
                
                if existing:
                    print(f"Contact with email {contact_data['email']} already exists")
                    return existing['contact_id']
                
                # Insert new contact
                cur.execute("""
                    INSERT INTO crm_contacts_cache 
                    (contact_id, name, first_name, last_name, company_name, 
                     email, phone, address, custom_fields, created_at, last_sync)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contact_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        company_name = EXCLUDED.company_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        address = EXCLUDED.address,
                        custom_fields = EXCLUDED.custom_fields,
                        last_sync = EXCLUDED.last_sync
                """, (
                    contact_data["contact_id"],
                    contact_data["name"],
                    contact_data["first_name"],
                    contact_data["last_name"],
                    contact_data["company_name"],
                    contact_data["email"],
                    contact_data["phone"],
                    contact_data["address"],
                    json.dumps(contact_data["custom_fields"]),
                    datetime.now(),
                    datetime.now()
                ))
                
                conn.commit()
                print(f"✅ Successfully added test contact: {contact_data['company_name']}")
                print(f"   Contact ID: {contact_data['contact_id']}")
                print(f"   Email: {contact_data['email']}")
                print(f"   Phone: {contact_data['phone']}")
                print(f"   Address: {contact_data['address']}")
                
                return contact_data["contact_id"]
                
    except Exception as e:
        print(f"❌ Error adding test contact: {e}")
        return None

if __name__ == "__main__":
    add_test_contact()