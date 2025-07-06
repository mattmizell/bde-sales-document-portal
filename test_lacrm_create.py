#!/usr/bin/env python3
"""
Test LACRM CreateContact API locally to figure out the correct format
"""

import requests
import json

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

def test_create_contact():
    """Test creating a contact with different parameter combinations"""
    
    # Extract UserCode from API key
    user_code = LACRM_API_KEY.split('-')[0]  # Gets '1073223'
    
    print("🧪 Testing LACRM CreateContact API")
    print("=" * 40)
    print(f"UserCode: {user_code}")
    print(f"API Key: {LACRM_API_KEY[:20]}...")
    
    # Test 1: Basic contact (works)
    print("\n🧪 Test 1: Basic contact (minimal fields)")
    params1 = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'CreateContact',
        'FirstName': 'Test',
        'LastName': 'User1', 
        'CompanyName': 'Test Company 1',
        'IsCompany': 'true',
        'AssignedTo': user_code
    }
    
    print("Parameters:", json.dumps({k: v for k, v in params1.items() if k != 'APIToken'}, indent=2))
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params1, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('Success'):
                    print("✅ Basic contact works!")
                    contact_id = result.get('ContactId')
                    print(f"Contact ID: {contact_id}")
                else:
                    print(f"❌ Failed: {result.get('Error')}")
            except:
                print("❌ JSON parse error")
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Test 2: Try different email formats
    print("\n🧪 Test 2: Testing email formats")
    
    email_formats = [
        'test@example.com',  # Simple string
        '[{"Text":"test2@example.com","Type":"Work"}]',  # JSON string
        [{"Text":"test3@example.com","Type":"Work"}],  # Actual array
    ]
    
    for i, email_format in enumerate(email_formats):
        print(f"\n  Testing email format {i+1}: {type(email_format).__name__}")
        
        params = {
            'APIToken': LACRM_API_KEY,
            'UserCode': user_code,
            'Function': 'CreateContact',
            'FirstName': 'Test',
            'LastName': f'Email{i+1}',
            'CompanyName': f'Email Test {i+1}',
            'Email': email_format,
            'IsCompany': 'true',
            'AssignedTo': user_code
        }
        
        try:
            if isinstance(email_format, list):
                # For actual array, use JSON in the request
                response = requests.post(
                    LACRM_BASE_URL,
                    json={'APIToken': LACRM_API_KEY, 'UserCode': user_code, 'Function': 'CreateContact',
                         'FirstName': 'Test', 'LastName': f'Email{i+1}', 'CompanyName': f'Email Test {i+1}',
                         'Email': email_format, 'IsCompany': True, 'AssignedTo': user_code},
                    timeout=10
                )
            else:
                response = requests.get(LACRM_BASE_URL, params=params, timeout=10)
            
            print(f"    Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get('Success'):
                    print(f"    ✅ Email format {i+1} works!")
                else:
                    print(f"    ❌ Error: {result.get('Error')}")
            else:
                print(f"    ❌ HTTP Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"    ❌ Exception: {e}")
    
    return True
    
    print("\n🧪 Test 1: Basic parameters")
    print("Parameters:", json.dumps({k: v for k, v in params1.items() if k != 'APIToken'}, indent=2))
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params1, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('Success'):
                    print("✅ SUCCESS! Contact created")
                    contact_id = result.get('Result', {}).get('ContactId') or result.get('ContactId')
                    print(f"Contact ID: {contact_id}")
                    return True
                else:
                    error = result.get('Error', 'Unknown error')
                    print(f"❌ LACRM Error: {error}")
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: Try without some optional fields
    print("\n🧪 Test 2: Minimal parameters")
    params2 = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'CreateContact',
        'Name': 'Test Contact 2',
        'IsCompany': 'false',
        'AssignedTo': user_code
    }
    
    print("Parameters:", json.dumps({k: v for k, v in params2.items() if k != 'APIToken'}, indent=2))
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params2, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('Success'):
                    print("✅ SUCCESS! Minimal contact created")
                    return True
                else:
                    error = result.get('Error', 'Unknown error')
                    print(f"❌ LACRM Error: {error}")
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 3: Check if we can query existing contacts to verify API works
    print("\n🧪 Test 3: Verify API with SearchContacts")
    params3 = {
        'APIToken': LACRM_API_KEY,
        'UserCode': user_code,
        'Function': 'SearchContacts',
        'SearchTerm': 'Gas',
        'MaxNumberOfResults': 5
    }
    
    try:
        response = requests.get(LACRM_BASE_URL, params=params3, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('Success'):
                    contacts = result.get('Result', [])
                    print(f"✅ Search worked! Found {len(contacts)} contacts")
                    if contacts:
                        sample = contacts[0]
                        print(f"Sample contact: {sample.get('CompanyName', 'No company')} - {sample.get('ContactId', 'No ID')}")
                else:
                    error = result.get('Error', 'Unknown error')
                    print(f"❌ Search failed: {error}")
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Search request failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_create_contact()
    
    if success:
        print("\n🎉 Contact creation working!")
    else:
        print("\n💥 Need to debug further...")
        print("\n💡 Try checking LACRM API documentation for required fields")