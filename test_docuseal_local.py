#!/usr/bin/env python3
"""
Test DocuSeal API directly to diagnose the 500 error
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Test configuration
DOCUSEAL_SERVICE_URL = os.getenv("DOCUSEAL_SERVICE_URL", "https://bde-docuseal-selfhosted.onrender.com")
DOCUSEAL_API_TOKEN = os.getenv("DOCUSEAL_API_TOKEN", "mHVsKRBH4EWVPEAxZ4nsVCa1WmAjZr4hhxj2MBWyCns")

print("🧪 Testing DocuSeal API Configuration")
print("=" * 50)
print(f"Service URL: {DOCUSEAL_SERVICE_URL}")
print(f"API Token: {DOCUSEAL_API_TOKEN[:20]}...")

# Test data
test_payload = {
    "template_id": "VmPsZnK4ARbXET",  # Customer Setup template
    "send_email": False,
    "submitters": [{
        "role": "First Party",
        "email": "matt.mizell@gmail.com",
        "name": "Gas O'Matt Store",
        "values": {
            "Company Name": "Gas O'Matt Store",
            "Contact Name": "Matt Mizell",
            "Email": "matt.mizell@gmail.com",
            "Phone": "(618) 555-0123",
            "Address": "1234 Highway 50 East",
            "City": "Mascoutah",
            "State": "IL",
            "Zip": "62258"
        }
    }]
}

headers = {
    "X-Auth-Token": DOCUSEAL_API_TOKEN,
    "Content-Type": "application/json"
}

api_url = f"{DOCUSEAL_SERVICE_URL}/api/submissions"

print(f"\n📮 Sending test request to: {api_url}")
print("Payload:", json.dumps(test_payload, indent=2))

try:
    response = requests.post(
        api_url,
        headers=headers,
        json=test_payload,
        timeout=30
    )
    
    print(f"\n📊 Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 201:
        result = response.json()
        print("\n✅ Success! DocuSeal submission created")
        print("Response:", json.dumps(result, indent=2))
        
        if result.get("submitters") and len(result["submitters"]) > 0:
            signing_url = result["submitters"][0].get("embed_src")
            print(f"\n🔗 Signing URL: {signing_url}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print("Response Text:", response.text)
        
        # Try to parse error response
        try:
            error_data = response.json()
            print("Error JSON:", json.dumps(error_data, indent=2))
        except:
            pass
            
except requests.exceptions.RequestException as e:
    print(f"\n❌ Request failed: {e}")
    print(f"Exception type: {type(e).__name__}")
    
print("\n🔍 Debugging tips:")
print("1. Check if DocuSeal is running at:", DOCUSEAL_SERVICE_URL)
print("2. Verify the API token is correct")
print("3. Check if the template ID exists: VmPsZnK4ARbXET")
print("4. Make sure the DocuSeal API is accessible from this network")