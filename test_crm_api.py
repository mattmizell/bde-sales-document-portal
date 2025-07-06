#!/usr/bin/env python3
"""
Quick CRM API Test
Test the CRM bridge endpoints with our cached data
"""

import requests
import json

def test_crm_endpoints():
    """Test the CRM API endpoints locally"""
    
    base_url = "http://127.0.0.1:8000/api/v1/crm"
    
    print("🧪 Testing CRM Bridge API Endpoints")
    print("=" * 40)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing CRM Health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health Status: {health.get('status')}")
            print(f"📊 Cache Stats: {health.get('cache_stats', {})}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Contact Search
    print("\n2️⃣ Testing Contact Search...")
    try:
        search_data = {
            "query": "gas",
            "limit": 5
        }
        
        response = requests.post(
            f"{base_url}/contacts/search", 
            json=search_data,
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            contacts = results.get('contacts', [])
            print(f"✅ Search for 'gas' found {len(contacts)} contacts:")
            
            for contact in contacts[:3]:  # Show first 3
                print(f"   • {contact.get('name')} - {contact.get('company_name')} - {contact.get('email')}")
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Search error: {e}")
    
    # Test 3: List Contacts
    print("\n3️⃣ Testing Contact List...")
    try:
        response = requests.get(f"{base_url}/contacts?limit=5", timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            contacts = results.get('contacts', [])
            print(f"✅ Listed {len(contacts)} contacts:")
            
            for contact in contacts:
                print(f"   • {contact.get('name')} - {contact.get('company_name')}")
        else:
            print(f"❌ List failed: {response.status_code}")
    except Exception as e:
        print(f"❌ List error: {e}")
    
    # Test 4: Stats
    print("\n4️⃣ Testing CRM Stats...")
    try:
        response = requests.get(f"{base_url}/stats", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            cache_stats = stats.get('cache_stats', {})
            print(f"✅ CRM Stats:")
            print(f"   📊 Total Contacts: {cache_stats.get('total_contacts')}")
            print(f"   📈 Cache Hit Rate: {cache_stats.get('cache_hit_rate')}%")
            print(f"   🕒 Cache Health: {cache_stats.get('cache_health')}")
        else:
            print(f"❌ Stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")

if __name__ == "__main__":
    print("🏢 BDE Sales Portal - CRM API Test")
    print("Testing cached CRM data with 2450+ contacts")
    
    test_crm_endpoints()
    
    print("\n🎉 CRM API tests complete!")
    print("Ready to move to next step!")