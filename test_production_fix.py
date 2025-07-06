#!/usr/bin/env python3
"""
Test the fixed create_contact_in_lacrm function locally
"""

import requests
import json
from datetime import datetime

# LACRM Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

def create_contact_in_lacrm(name, email=None, phone=None, company_name=None, address=None):
    """Create new contact in LACRM with proper API handling - EXACT copy from main.py"""
    try:
        # Extract UserCode from API key
        user_code = LACRM_API_KEY.split('-')[0]  # Gets '1073223'
        
        # Split name into first/last if provided as full name
        first_name = ""
        last_name = ""
        if name:
            parts = name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
        
        # LACRM requires POST with JSON for array fields (email, phone, address)
        payload = {
            'APIToken': LACRM_API_KEY,
            'UserCode': user_code,
            'Function': 'CreateContact',
            'FirstName': first_name,
            'LastName': last_name,
            'CompanyName': company_name or "Gas O Matt",  # Default company name
            'IsCompany': True,  # Always true since we're creating business contacts
            'AssignedTo': user_code
        }
        
        # Add array fields if provided
        if email:
            payload['Email'] = [{"Text": email, "Type": "Work"}]
        if phone:
            payload['Phone'] = [{"Text": phone, "Type": "Work"}]
        if address:
            # Parse address if it's a simple string
            payload['Address'] = [{"Street": address, "Type": "Work"}]
        
        print("Testing payload:", json.dumps({k: v for k, v in payload.items() if k != 'APIToken'}, indent=2))
        
        response = requests.post(
            LACRM_BASE_URL,
            json=payload,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        # Handle LACRM response quirks - manually parse JSON
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM creation failed: {error_msg}")
        
        contact_id = result.get("ContactId")
        
        print(f"✅ Contact created in LACRM: {contact_id}")
        
        return {
            "contact_id": contact_id,
            "name": name,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "source": "lacrm_api"
        }
        
    except Exception as e:
        print(f"❌ Contact creation failed: {e}")
        raise

if __name__ == "__main__":
    print("🧪 Testing Production Fix for Gas O Matt")
    print("=" * 50)
    
    try:
        result = create_contact_in_lacrm(
            name="Matt Mizell", 
            email="matt.mizell@gmail.com",
            phone="(618) 555-0123", 
            company_name="Gas O Matt",
            address="1234 Highway 50 East, Mascoutah, IL 62258"
        )
        
        print("🎉 SUCCESS! Production fix works locally")
        print(f"Contact ID: {result['contact_id']}")
        
    except Exception as e:
        print(f"💥 Production fix failed: {e}")