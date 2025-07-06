#!/usr/bin/env python3
"""
Full CRM Sync with LACRM Pagination
Uses proven pagination logic from backup system
"""

import os
import requests
import json
from datetime import datetime
from database.connection import SessionLocal
from database.models import CRMContactsCache

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

def sync_all_crm_contacts():
    """Sync all contacts from LACRM using proper pagination"""
    
    print("🔄 Full CRM Sync with LACRM Pagination")
    print("=" * 50)
    
    try:
        # Extract UserCode from API key
        user_code = LACRM_API_KEY.split('-')[0]  # Gets '1073223'
        
        # Use SearchContacts with proper pagination to get ALL contacts
        all_customers = {}  # Use dict to deduplicate by ContactId
        
        print("🔍 Using SearchContacts with proper pagination...")
        
        page = 1
        max_results_per_page = 10000  # LACRM API maximum
        total_retrieved = 0
        
        while True:
            print(f"\n📄 Fetching page {page} (requesting up to {max_results_per_page} records)...")
            
            params = {
                'APIToken': LACRM_API_KEY,
                'UserCode': user_code,
                'Function': 'SearchContacts',
                'SearchTerm': '',  # Empty to get all contacts
                'MaxNumberOfResults': max_results_per_page,
                'Page': page
            }
            
            try:
                response = requests.get(LACRM_BASE_URL, params=params, timeout=30)
                
                print(f"📊 Response Status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ API error: {response.status_code} - {response.text[:200]}...")
                    break
                
                # Parse JSON response
                try:
                    result_data = json.loads(response.text)
                    print(f"🔧 API Response keys: {list(result_data.keys())}")
                    if 'HasMoreResults' in result_data:
                        print(f"📄 HasMoreResults: {result_data.get('HasMoreResults')}")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing failed: {e}")
                    break
                
                if not result_data.get('Success'):
                    print(f"❌ CRM API failed: {result_data.get('Error', 'Unknown error')}")
                    break
                
                customers_data = result_data.get('Result', [])
                
                if not isinstance(customers_data, list):
                    customers_data = [customers_data] if customers_data else []
                
                print(f"✅ Retrieved {len(customers_data)} customers from page {page}")
                
                # If we got no results, we've reached the end
                if len(customers_data) == 0:
                    print("📋 No more customers found - reached end of data")
                    break
                
                # Add to our deduplicated collection
                new_customers = 0
                for customer in customers_data:
                    contact_id = str(customer.get('ContactId', ''))
                    if contact_id and contact_id not in all_customers:
                        all_customers[contact_id] = customer
                        new_customers += 1
                
                total_retrieved += new_customers
                print(f"📊 Added {new_customers} new unique customers")
                print(f"📊 Total unique customers so far: {len(all_customers)}")
                
                # Show a sample customer from this page
                if len(customers_data) > 0:
                    sample_customer = customers_data[0]
                    name = sample_customer.get('CompanyName', 'No name')
                    contact_id = sample_customer.get('ContactId', 'No ID')
                    print(f"📋 Sample from page {page}: {name} - ID: {contact_id}")
                
                # Move to next page
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 100:  # 100 pages should be plenty for most CRMs
                    print("⚠️ Safety limit reached - stopping pagination")
                    break
                
            except Exception as e:
                print(f"❌ Page {page} fetch failed: {e}")
                break
        
        # Convert back to list
        customers_list = list(all_customers.values())
        print(f"\n🎉 Pagination complete!")
        print(f"📊 Total pages fetched: {page - 1}")
        print(f"📊 Final result: {len(customers_list)} unique customers found")
        
        # Clear existing cache and insert fresh data
        print("\n💾 Updating database cache...")
        
        session = SessionLocal()
        
        # Clear existing cache
        print("🧹 Clearing existing cache...")
        session.query(CRMContactsCache).delete()
        session.commit()
        
        # Insert all customers
        inserted_count = 0
        skipped_count = 0
        
        for customer in customers_list:
            try:
                # Extract customer data using LACRM format
                contact_id = str(customer.get('ContactId', ''))
                
                # Extract company name
                company_name = str(customer.get('CompanyName', '') or '')
                if not company_name and customer.get('Company Name'):
                    company_name = str(customer['Company Name'])
                
                # Extract name - prefer individual first/last name
                name = company_name or 'Unknown Contact'  # Default to company name
                first_name = ""
                last_name = ""
                
                if isinstance(customer.get('Name'), dict):
                    name_obj = customer['Name']
                    first_name = name_obj.get('FirstName', '')
                    last_name = name_obj.get('LastName', '')
                    if first_name or last_name:
                        name = f"{first_name} {last_name}".strip()
                elif customer.get('Name'):
                    name = str(customer['Name'])
                
                # Extract email (LACRM format: list of dicts with 'Text' field)
                email = ""
                email_raw = customer.get('Email', '')
                if isinstance(email_raw, list) and len(email_raw) > 0:
                    first_email = email_raw[0]
                    if isinstance(first_email, dict):
                        email_text = first_email.get('Text', '')
                        email = email_text.split(' (')[0] if email_text else ''
                    else:
                        email = str(first_email)
                elif isinstance(email_raw, dict):
                    email = str(email_raw.get('Text', '') or '')
                else:
                    email = str(email_raw or '')
                
                # Extract phone (LACRM format: list of dicts with 'Text' field)
                phone = ""
                phone_raw = customer.get('Phone', '')
                if isinstance(phone_raw, list) and len(phone_raw) > 0:
                    first_phone = phone_raw[0]
                    if isinstance(first_phone, dict):
                        phone_text = first_phone.get('Text', '')
                        phone = phone_text.split(' (')[0] if phone_text else ''
                    else:
                        phone = str(first_phone)
                elif isinstance(phone_raw, dict):
                    phone = str(phone_raw.get('Text', '') or '')
                else:
                    phone = str(phone_raw or '')
                
                # Extract address (LACRM format: list of dicts)
                address_data = None
                address_raw = customer.get('Address', '')
                if isinstance(address_raw, list) and len(address_raw) > 0:
                    first_address = address_raw[0]
                    if isinstance(first_address, dict):
                        address_data = {
                            "street_address": first_address.get('Street', ''),
                            "city": first_address.get('City', ''),
                            "state": first_address.get('State', ''),
                            "zip_code": first_address.get('Zip', ''),
                            "country": first_address.get('Country', ''),
                            "type": first_address.get('Type', 'Work')
                        }
                
                # Skip if no essential data
                if not contact_id or not name:
                    skipped_count += 1
                    continue
                
                # Create cache entry
                cache_entry = CRMContactsCache(
                    contact_id=contact_id,
                    name=name,
                    first_name=first_name,
                    last_name=last_name,
                    company_name=company_name,
                    email=email,
                    phone=phone,
                    address=address_data,
                    sync_status='synced',
                    last_sync=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                session.add(cache_entry)
                inserted_count += 1
                
                # Show progress every 100 records
                if inserted_count % 100 == 0:
                    print(f"  📋 Processed {inserted_count} customers...")
                    session.commit()  # Commit in batches
                
            except Exception as e:
                print(f"⚠️ Error processing customer {customer.get('ContactId', 'unknown')}: {e}")
                skipped_count += 1
                continue
        
        # Final commit
        session.commit()
        session.close()
        
        print(f"\n🎉 CRM Full Sync Complete!")
        print(f"✅ Successfully cached: {inserted_count} customers")
        print(f"⚠️ Skipped (incomplete data): {skipped_count} records")
        print(f"🗄️ Database ready for fast customer lookups")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Full sync failed: {e}")
        return False

def test_synced_cache():
    """Test the synced cache"""
    print("\n🔍 Testing synced cache...")
    
    try:
        session = SessionLocal()
        
        # Count total
        total_count = session.query(CRMContactsCache).count()
        print(f"📊 Total cached contacts: {total_count}")
        
        # Sample some contacts
        sample_contacts = session.query(CRMContactsCache).limit(5).all()
        
        print("📋 Sample contacts:")
        for contact in sample_contacts:
            print(f"   • {contact.name} - {contact.company_name or 'No Company'} - {contact.email}")
        
        # Test search functionality
        print("\n🔍 Testing search...")
        search_results = session.query(CRMContactsCache).filter(
            CRMContactsCache.company_name.ilike('%gas%')
        ).limit(3).all()
        
        print(f"📋 'gas' search results ({len(search_results)}):")
        for contact in search_results:
            print(f"   • {contact.name} - {contact.company_name}")
        
        session.close()
        print("✅ Cache test completed!")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")

if __name__ == "__main__":
    print("🏢 BDE Sales Portal - Full CRM Sync")
    print("=" * 40)
    
    success = sync_all_crm_contacts()
    
    if success:
        test_synced_cache()
        print("\n🚀 CRM cache is now fully populated!")
        print("Ready to test API endpoints...")
    else:
        print("\n💥 Sync failed!")
        exit(1)