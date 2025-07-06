#!/usr/bin/env python3
"""
Search for Gas O Matt contact in LACRM by email to find correct ID
"""

import requests
import json

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

def search_contact_by_email():
    """Search for contact by email in LACRM"""
    
    user_code = LACRM_API_KEY.split('-')[0]
    
    print("🔍 Searching for Gas O Matt contact in LACRM")
    print("=" * 50)
    
    params = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'SearchContacts',
        'SearchTerm': 'matt.mizell@gmail.com',
        'MaxNumberOfResults': 10
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                contacts = result.get('Result', [])
                
                print(f"\n📋 Found {len(contacts)} contacts:")
                for i, contact in enumerate(contacts):
                    print(f"\n  Contact #{i+1}:")
                    print(f"    Contact ID: {contact.get('ContactId', 'N/A')}")
                    print(f"    Name: {contact.get('Name', 'N/A')}")
                    print(f"    Company Name: {contact.get('CompanyName', 'N/A')}")
                    print(f"    Email: {contact.get('Email', 'N/A')}")
                    print(f"    Phone: {contact.get('Phone', 'N/A')}")
                    print(f"    Is Company: {contact.get('IsCompany', 'N/A')}")
                
                if contacts:
                    # Show full data for first contact
                    print(f"\n🔧 Full data for first contact:")
                    print(json.dumps(contacts[0], indent=2))
                
                return contacts
            else:
                print(f"❌ SearchContacts failed: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return []

def test_update_with_correct_id(contact_id):
    """Test updating contact with correct ID"""
    
    user_code = LACRM_API_KEY.split('-')[0]
    
    print(f"\n🧪 Testing update with Contact ID: {contact_id}")
    
    payload = {
        "APIToken": LACRM_API_KEY,
        "UserCode": user_code,
        "Function": "EditContact",
        "ContactId": contact_id,
        "FirstName": "Matt",
        "LastName": "Mizell", 
        "CompanyName": "Gas O'Matt Store",
        "IsCompany": True
    }
    
    try:
        response = requests.post(LACRM_BASE_URL, json=payload, timeout=10)
        print(f"Update Status: {response.status_code}")
        print(f"Update Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                print("✅ Update successful!")
                return True
            else:
                print(f"❌ Update failed: {result.get('Error')}")
        
    except Exception as e:
        print(f"❌ Update exception: {e}")
    
    return False

if __name__ == "__main__":
    contacts = search_contact_by_email()
    
    if contacts:
        print("\n✅ Found contacts!")
        
        # Try to update the first contact found
        first_contact = contacts[0]
        contact_id = first_contact.get('ContactId')
        
        if contact_id:
            print(f"\nUsing Contact ID: {contact_id}")
            success = test_update_with_correct_id(contact_id)
            
            if success:
                print("\n🎉 Contact update successful!")
            else:
                print("\n❌ Contact update failed")
        else:
            print("\n❌ No Contact ID found")
    else:
        print("\n❌ No contacts found")