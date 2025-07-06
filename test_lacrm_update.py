#!/usr/bin/env python3
"""
Test LACRM contact UPDATE functionality with Gas O Matt
"""

import requests
import json
from datetime import datetime

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

# Gas O Matt contact ID from database
GAS_O_MATT_CONTACT_ID = "4036857411931183467036798214340"

def test_update_contact():
    """Test updating the Gas O Matt contact"""
    
    user_code = LACRM_API_KEY.split('-')[0]
    
    print("🧪 Testing LACRM Contact UPDATE")
    print("=" * 50)
    print(f"Contact ID: {GAS_O_MATT_CONTACT_ID}")
    print(f"UserCode: {user_code}")
    
    # Test 1: Try the EditContact function as in main.py
    print("\n🧪 Test 1: EditContact function (current main.py approach)")
    
    payload_v1 = {
        "APIToken": LACRM_API_KEY,
        "UserCode": user_code,
        "Function": "EditContact",
        "ContactId": GAS_O_MATT_CONTACT_ID,
        "FirstName": "Matt",
        "LastName": "Mizell", 
        "CompanyName": "Gas O Matt",
        "IsCompany": True
    }
    
    print("Payload:", json.dumps({k: v for k, v in payload_v1.items() if k != 'APIToken'}, indent=2))
    
    try:
        response = requests.post(LACRM_BASE_URL, json=payload_v1, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                print("✅ EditContact method works!")
                return True
            else:
                print(f"❌ EditContact failed: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Try GET method with EditContact parameters  
    print("\n🧪 Test 2: EditContact with GET method")
    
    params_v2 = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'EditContact',
        'ContactId': GAS_O_MATT_CONTACT_ID,
        'FirstName': 'Matt',
        'LastName': 'Mizell',
        'CompanyName': 'Gas O Matt Store',
        'IsCompany': 'true'
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params_v2, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                print("✅ GET EditContact method works!")
                return True
            else:
                print(f"❌ GET EditContact failed: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Check what update methods are available
    print("\n🧪 Test 3: Get contact details to see current state")
    
    get_params = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'GetContact',
        'ContactId': GAS_O_MATT_CONTACT_ID
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=get_params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('Success'):
                contact_data = result.get('Result', {})
                print("Current contact data:", json.dumps(contact_data, indent=2))
            else:
                print(f"❌ GetContact failed: {result.get('Error')}")
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

if __name__ == "__main__":
    success = test_update_contact()
    
    if success:
        print("\n🎉 Found working update method!")
    else:
        print("\n💥 Need to debug update functionality...")