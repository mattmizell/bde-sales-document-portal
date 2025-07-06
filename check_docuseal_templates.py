#!/usr/bin/env python3
"""
Check what templates are available in DocuSeal
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DOCUSEAL_SERVICE_URL = "https://bde-docuseal-selfhosted.onrender.com"
DOCUSEAL_API_TOKEN = os.getenv("DOCUSEAL_API_TOKEN")

headers = {
    "X-Auth-Token": DOCUSEAL_API_TOKEN,
    "Content-Type": "application/json"
}

print("🔍 Checking DocuSeal Templates")
print("=" * 50)

try:
    # Get templates list
    response = requests.get(
        f"{DOCUSEAL_SERVICE_URL}/api/templates",
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        templates = response.json()
        
        if isinstance(templates, list):
            print(f"\n✅ Found {len(templates)} templates:\n")
            
            for i, template in enumerate(templates):
                print(f"Template #{i+1}:")
                print(f"  ID: {template.get('id')}")
                print(f"  Name: {template.get('name')}")
                print(f"  Slug: {template.get('slug')}")
                print(f"  Created: {template.get('created_at')}")
                print()
                
            # Create mapping recommendations
            print("\n📋 Recommended mapping for main.py:")
            print("template_mapping = {")
            
            for template in templates:
                name = template.get('name', '').lower()
                template_id = template.get('id')
                
                # Try to map based on name
                if 'customer' in name and 'setup' in name:
                    print(f'    "customer_setup": {template_id},  # {template.get("name")}')
                elif 'eft' in name:
                    print(f'    "eft_auth": {template_id},  # {template.get("name")}')
                elif 'p66' in name or 'phillips' in name:
                    print(f'    "p66_loi": {template_id},  # {template.get("name")}')
                elif 'vp' in name or 'racing' in name:
                    print(f'    "vp_loi": {template_id},  # {template.get("name")}')
                else:
                    print(f'    # "{template.get("name")}": {template_id},')
                    
            print("}")
            
        else:
            print(f"Unexpected response format: {type(templates)}")
            print(f"Response: {json.dumps(templates, indent=2)}")
    else:
        print(f"❌ Error getting templates: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
    
print("\n💡 Note: If EFT template is not ID 2, update the mapping in main.py")