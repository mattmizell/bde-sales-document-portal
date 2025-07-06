#!/usr/bin/env python3
"""
Simple CRM Bridge Test
Test LACRM connection and cache some contacts
"""

import os
import requests
import json
from datetime import datetime
from database.connection import SessionLocal, test_connection
from database.models import CRMContactsCache

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com/v2/"

def test_database():
    """Test database connection"""
    print("1️⃣ Testing database connection...")
    
    result = test_connection()
    if result["status"] == "healthy":
        print("✅ Database connection successful")
        return True
    else:
        print(f"❌ Database connection failed: {result['error']}")
        return False

def test_lacrm_api():
    """Test LACRM API connection"""
    print("\n2️⃣ Testing LACRM API connection...")
    
    try:
        # Extract UserCode from API key
        user_code = LACRM_API_KEY.split('-')[0]  # Gets '1073223'
        
        params = {
            'APIToken': LACRM_API_KEY,
            'UserCode': user_code,
            'Function': 'GetContacts',
            'NumRows': 5  # Just get 5 contacts for testing
        }
        
        response = requests.post(LACRM_BASE_URL, data=params, timeout=30)
        
        if response.status_code == 200:
            data = json.loads(response.text)
            
            # LACRM returns results directly, not in a Success wrapper
            if 'Results' in data:
                contacts = data.get('Results', [])
                print(f"✅ LACRM API connected successfully")
                print(f"📊 Retrieved {len(contacts)} test contacts")
                return contacts
            elif data.get('Success'):
                contacts = data.get('Result', [])
                print(f"✅ LACRM API connected successfully")
                print(f"📊 Retrieved {len(contacts)} test contacts")
                return contacts
            else:
                print(f"❌ LACRM API error: {data}")
                return None
        else:
            print(f"❌ LACRM API HTTP error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ LACRM API connection failed: {e}")
        return None

def cache_test_contacts(contacts):
    """Cache some test contacts"""
    print(f"\n3️⃣ Caching {len(contacts)} test contacts...")
    
    try:
        session = SessionLocal()
        cached_count = 0
        
        for contact in contacts[:5]:  # Cache first 5 contacts
            try:
                # Extract contact data from LACRM format
                contact_id = contact.get('ContactId')
                
                # Extract company name
                company_name = ""
                if contact.get('CompanyName'):
                    company_name = contact['CompanyName']
                elif contact.get('Company Name'):
                    company_name = contact['Company Name']
                
                # Extract name
                name = 'Unknown'
                first_name = ""
                last_name = ""
                
                if isinstance(contact.get('Name'), dict):
                    name_obj = contact['Name']
                    first_name = name_obj.get('FirstName', '')
                    last_name = name_obj.get('LastName', '')
                    name = f"{first_name} {last_name}".strip() or 'Unknown'
                elif contact.get('Name'):
                    name = str(contact['Name'])
                
                # Extract email and phone
                email = ""
                if contact.get('Email') and isinstance(contact['Email'], list) and len(contact['Email']) > 0:
                    email = contact['Email'][0].get('Text', '').split(' (')[0]  # Remove (Work) suffix
                
                phone = ""
                if contact.get('Phone') and isinstance(contact['Phone'], list) and len(contact['Phone']) > 0:
                    phone = contact['Phone'][0].get('Text', '').split(' (')[0]  # Remove (Work) suffix
                
                # Create cache entry
                cache_entry = CRMContactsCache(
                    contact_id=contact_id,
                    name=name,
                    first_name=first_name,
                    last_name=last_name,
                    company_name=company_name,
                    email=email,
                    phone=phone,
                    sync_status='synced',
                    last_sync=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                # Upsert (insert or update)
                existing = session.query(CRMContactsCache).filter(
                    CRMContactsCache.contact_id == contact_id
                ).first()
                
                if existing:
                    # Update existing
                    existing.name = name
                    existing.first_name = first_name
                    existing.last_name = last_name
                    existing.company_name = company_name
                    existing.email = email
                    existing.phone = phone
                    existing.last_sync = datetime.utcnow()
                else:
                    # Insert new
                    session.add(cache_entry)
                
                cached_count += 1
                print(f"   ✓ Cached: {name} ({company_name or 'No Company'})")
                
            except Exception as e:
                print(f"   ❌ Failed to cache contact {contact.get('ContactId', 'Unknown')}: {e}")
                continue
        
        session.commit()
        session.close()
        
        print(f"✅ Successfully cached {cached_count} contacts")
        return cached_count
        
    except Exception as e:
        print(f"❌ Caching failed: {e}")
        return 0

def test_cache_query():
    """Test querying the cache"""
    print("\n4️⃣ Testing cache queries...")
    
    try:
        session = SessionLocal()
        
        # Count total cached contacts
        total_count = session.query(CRMContactsCache).count()
        print(f"📊 Total cached contacts: {total_count}")
        
        # Get first 3 contacts
        contacts = session.query(CRMContactsCache).limit(3).all()
        
        print("📋 Sample cached contacts:")
        for contact in contacts:
            print(f"   • {contact.name} - {contact.company_name or 'No Company'} - {contact.email}")
        
        session.close()
        
        print("✅ Cache queries working!")
        return True
        
    except Exception as e:
        print(f"❌ Cache query failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🏢 BDE CRM Bridge - Connection Test")
    print("=" * 40)
    
    # Test database
    if not test_database():
        return False
    
    # Test LACRM API
    contacts = test_lacrm_api()
    if not contacts:
        return False
    
    # Cache test contacts
    cached_count = cache_test_contacts(contacts)
    if cached_count == 0:
        return False
    
    # Test cache queries
    if not test_cache_query():
        return False
    
    print("\n🎉 All tests passed!")
    print("✅ Database: Connected")
    print("✅ LACRM API: Connected")
    print("✅ Cache: Working")
    print("\n🚀 Ready to start CRM bridge service!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)