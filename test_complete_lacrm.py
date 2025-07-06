#!/usr/bin/env python3
"""
Test complete LACRM contact creation with all fields
"""

import requests
import json

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

def create_complete_contact():
    """Test creating Gas O Matt with all fields"""
    
    user_code = LACRM_API_KEY.split('-')[0]
    
    print("🧪 Testing Complete LACRM Contact Creation")
    print("=" * 50)
    
    # Method 1: Use POST with JSON for arrays
    print("\n🧪 Method 1: POST + JSON (for arrays)")
    
    payload = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'CreateContact',
        'FirstName': 'Matt',
        'LastName': 'Mizell',
        'CompanyName': 'Gas O Matt',
        'Email': [{"Text": "matt.mizell@gmail.com", "Type": "Work"}],
        'Phone': [{"Text": "(618) 555-0123", "Type": "Work"}],
        'Address': [{"Street": "1234 Highway 50 East", "City": "Mascoutah", "State": "IL", "Zip": "62258", "Type": "Work"}],
        'IsCompany': True,
        'AssignedTo': user_code
    }
    
    print("Payload:", json.dumps({k: v for k, v in payload.items() if k != 'APIToken'}, indent=2))
    
    try:
        response = requests.post(LACRM_BASE_URL, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                contact_id = result.get('ContactId')
                print(f"✅ SUCCESS! Created complete contact: {contact_id}")
                return True
            else:
                print(f"❌ LACRM Error: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Method 2: Hybrid - GET for basic, then update with details
    print("\n🧪 Method 2: Hybrid approach (GET basic + update)")
    
    # First create basic contact with GET
    basic_params = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'CreateContact',
        'FirstName': 'Matt',
        'LastName': 'Mizell Hybrid',
        'CompanyName': 'Gas O Matt Hybrid',
        'IsCompany': 'true',
        'AssignedTo': user_code
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=basic_params, timeout=10)
        print(f"Basic contact status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                contact_id = result.get('ContactId')
                print(f"✅ Basic contact created: {contact_id}")
                
                # Now try to update with email/phone using EditContact
                update_payload = {
                    'APIToken': LACRM_API_KEY,
                    'UserCode': user_code,
                    'Function': 'EditContact',
                    'ContactId': contact_id,
                    'Email': [{"Text": "matt.mizell+hybrid@gmail.com", "Type": "Work"}],
                    'Phone': [{"Text": "(618) 555-0125", "Type": "Work"}]
                }
                
                update_response = requests.post(LACRM_BASE_URL, json=update_payload, timeout=10)
                print(f"Update status: {update_response.status_code}")
                print(f"Update response: {update_response.text}")
                
                if update_response.status_code == 200:
                    update_result = update_response.json()
                    if update_result.get('Success'):
                        print("✅ Contact updated with email/phone!")
                        return True
                    else:
                        print(f"❌ Update failed: {update_result.get('Error')}")
                        
    except Exception as e:
        print(f"❌ Hybrid method failed: {e}")
    
    return False

if __name__ == "__main__":
    success = create_complete_contact()
    
    if success:
        print("\n🎉 Found working method for complete contact creation!")
    else:
        print("\n💥 Need to debug further...")