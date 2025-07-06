#!/usr/bin/env python3
"""
Test different DocuSeal API payload formats
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DOCUSEAL_SERVICE_URL = "https://bde-docuseal-selfhosted.onrender.com"
DOCUSEAL_API_TOKEN = "mHVsKRBH4EWVPEAxZ4nsVCa1WmAjZr4hhxj2MBWyCns"

headers = {
    "X-Auth-Token": DOCUSEAL_API_TOKEN,
    "Content-Type": "application/json"
}

# Test different payload formats
test_formats = [
    # Format 1: Direct template_id
    {
        "name": "Direct template_id",
        "payload": {
            "template_id": "VmPsZnK4ARbXET",
            "send_email": False,
            "submitters": [{
                "role": "First Party",
                "email": "test@example.com",
                "name": "Test User"
            }]
        }
    },
    # Format 2: Wrapped in submission
    {
        "name": "Wrapped in submission",
        "payload": {
            "submission": {
                "template_id": "VmPsZnK4ARbXET",
                "send_email": False,
                "submitters": [{
                    "role": "First Party",
                    "email": "test@example.com",
                    "name": "Test User"
                }]
            }
        }
    },
    # Format 3: Template ID as number
    {
        "name": "Template ID as number",
        "payload": {
            "template_id": 1,  # Try as number
            "send_email": False,
            "submitters": [{
                "role": "First Party",
                "email": "test@example.com",
                "name": "Test User"
            }]
        }
    },
    # Format 4: With template instead of template_id
    {
        "name": "Using 'template' field",
        "payload": {
            "template": "VmPsZnK4ARbXET",
            "send_email": False,
            "submitters": [{
                "role": "First Party",
                "email": "test@example.com",
                "name": "Test User"
            }]
        }
    }
]

print("🧪 Testing DocuSeal API Payload Formats")
print("=" * 50)

for test in test_formats:
    print(f"\n📋 Test: {test['name']}")
    print(f"Payload: {json.dumps(test['payload'], indent=2)}")
    
    try:
        response = requests.post(
            f"{DOCUSEAL_SERVICE_URL}/api/submissions",
            headers=headers,
            json=test['payload'],
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print("✅ Success!")
            print(f"Response: {response.text[:200]}...")
            break
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

# Also test getting templates list
print("\n\n🔍 Testing Templates Endpoint")
print("=" * 50)

try:
    response = requests.get(
        f"{DOCUSEAL_SERVICE_URL}/api/templates",
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        templates = response.json()
        print(f"✅ Found {len(templates)} templates:")
        for template in templates[:5]:  # Show first 5
            print(f"  • ID: {template.get('id')} - Name: {template.get('name')}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")