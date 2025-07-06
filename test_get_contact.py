#!/usr/bin/env python3
"""
Test getting contact data directly from LACRM to verify update worked
"""

import requests
import json

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

# Gas O Matt contact ID
GAS_O_MATT_CONTACT_ID = "4036857411931183467036798214340"

def get_contact_from_lacrm():
    """Get contact data directly from LACRM"""
    
    user_code = LACRM_API_KEY.split('-')[0]
    
    print("🔍 Getting Gas O Matt contact from LACRM")
    print("=" * 50)
    
    params = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'GetContact',
        'ContactId': GAS_O_MATT_CONTACT_ID
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                contact_data = result.get('Result', {})
                
                print("\n📋 Current LACRM Contact Data:")
                print(f"  Contact ID: {contact_data.get('ContactId', 'N/A')}")
                print(f"  Name: {contact_data.get('Name', 'N/A')}")
                print(f"  Company Name: {contact_data.get('CompanyName', 'N/A')}")
                print(f"  Email: {contact_data.get('Email', 'N/A')}")
                print(f"  Phone: {contact_data.get('Phone', 'N/A')}")
                print(f"  Address: {contact_data.get('Address', 'N/A')}")
                print(f"  Is Company: {contact_data.get('IsCompany', 'N/A')}")
                
                # Show full raw data for debugging
                print("\n🔧 Full Raw Contact Data:")
                print(json.dumps(contact_data, indent=2))
                
                return contact_data
            else:
                print(f"❌ GetContact failed: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return None

if __name__ == "__main__":
    contact_data = get_contact_from_lacrm()
    
    if contact_data:
        print("\n✅ Successfully retrieved contact data from LACRM!")
        
        # Check if our update worked
        company_name = contact_data.get('CompanyName', '')
        if 'Gas O Matt' in str(company_name):
            print("🎉 Update successful - Company name contains 'Gas O Matt'!")
        else:
            print("⚠️ Update may not have worked - Company name doesn't contain 'Gas O Matt'")
    else:
        print("\n❌ Failed to retrieve contact data")