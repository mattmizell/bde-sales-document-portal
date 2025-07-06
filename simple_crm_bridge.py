#!/usr/bin/env python3
"""
Simple CRM Bridge - Zero Dependencies Hell
Direct HTTP requests to Less Annoying CRM with PostgreSQL caching
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Configuration
LACRM_API_KEY = "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W"
LACRM_BASE_URL = "https://api.lessannoyingcrm.com/v2/"
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'
)

class SimpleCRMBridge:
    """Simple CRM bridge with direct HTTP and PostgreSQL"""
    
    def __init__(self):
        self.api_key = LACRM_API_KEY
        self.base_url = LACRM_BASE_URL
        self.timeout = 30
        
    def get_db_connection(self):
        """Get direct PostgreSQL connection"""
        try:
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def search_contacts(self, query: str = None, limit: int = 50) -> List[Dict]:
        """Search contacts in cache"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    if query:
                        cur.execute("""
                            SELECT contact_id, name, first_name, last_name, 
                                   company_name, email, phone, address, 
                                   created_at, last_sync
                            FROM crm_contacts_cache 
                            WHERE name ILIKE %s 
                               OR company_name ILIKE %s 
                               OR email ILIKE %s
                            ORDER BY name
                            LIMIT %s
                        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                    else:
                        cur.execute("""
                            SELECT contact_id, name, first_name, last_name, 
                                   company_name, email, phone, address, 
                                   created_at, last_sync
                            FROM crm_contacts_cache 
                            ORDER BY name
                            LIMIT %s
                        """, (limit,))
                    
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Contact search failed: {e}")
            return []
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict]:
        """Get single contact by ID"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT contact_id, name, first_name, last_name, 
                               company_name, email, phone, address, 
                               created_at, last_sync
                        FROM crm_contacts_cache 
                        WHERE contact_id = %s
                    """, (contact_id,))
                    
                    row = cur.fetchone()
                    return dict(row) if row else None
                    
        except Exception as e:
            logger.error(f"Contact lookup failed: {e}")
            return None
    
    def create_contact_in_lacrm(self, name: str, email: str = None, phone: str = None, 
                               company_name: str = None) -> Dict:
        """Create contact in LACRM"""
        try:
            payload = {
                "Function": "CreateContact",
                "Parameters": {
                    "Name": name,
                    "Email": email or "",
                    "Phone": phone or "",
                    "CompanyName": company_name or ""
                }
            }
            
            response = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"LACRM API error: {response.status_code}")
            
            result = response.json()
            
            if not result.get("Success"):
                raise Exception(f"Contact creation failed: {result.get('Errors')}")
            
            contact_id = result.get("ContactId")
            
            # Cache the new contact
            self._cache_contact(contact_id, name, email, phone, company_name)
            
            return {
                "contact_id": contact_id,
                "name": name,
                "email": email,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Contact creation failed: {e}")
            raise
    
    def sync_all_contacts(self) -> Dict:
        """Sync all contacts from LACRM"""
        try:
            payload = {
                "Function": "GetContacts",
                "Parameters": {
                    "Sort": "Name",
                    "NumRows": 2000
                }
            }
            
            response = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"LACRM API error: {response.status_code}")
            
            result = response.json()
            
            if not result.get("Success"):
                raise Exception(f"Sync failed: {result.get('Errors')}")
            
            contacts = result.get("Result", [])
            
            # Update cache
            updated_count = 0
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    for contact in contacts:
                        try:
                            cur.execute("""
                                INSERT INTO crm_contacts_cache 
                                (contact_id, name, first_name, last_name, company_name, 
                                 email, phone, address, last_sync, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (contact_id) 
                                DO UPDATE SET
                                    name = EXCLUDED.name,
                                    first_name = EXCLUDED.first_name,
                                    last_name = EXCLUDED.last_name,
                                    company_name = EXCLUDED.company_name,
                                    email = EXCLUDED.email,
                                    phone = EXCLUDED.phone,
                                    address = EXCLUDED.address,
                                    last_sync = EXCLUDED.last_sync
                            """, (
                                contact.get("ContactId"),
                                contact.get("Name", ""),
                                contact.get("FirstName", ""),
                                contact.get("LastName", ""),
                                contact.get("CompanyName", ""),
                                contact.get("Email", ""),
                                contact.get("Phone", ""),
                                json.dumps(contact.get("Address", {})),
                                datetime.now(),
                                datetime.now()
                            ))
                            updated_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to cache contact {contact.get('ContactId')}: {e}")
                            continue
                
                conn.commit()
            
            logger.info(f"Synced {updated_count} contacts from LACRM")
            return {
                "synced_count": updated_count,
                "total_contacts": len(contacts),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM crm_contacts_cache")
                    total_contacts = cur.fetchone()[0]
                    
                    cur.execute("SELECT MAX(last_sync) FROM crm_contacts_cache")
                    last_sync = cur.fetchone()[0]
                    
                    return {
                        "total_contacts": total_contacts,
                        "last_sync": last_sync.isoformat() if last_sync else None,
                        "cache_health": "healthy" if total_contacts > 0 else "empty"
                    }
                    
        except Exception as e:
            logger.error(f"Stats failed: {e}")
            return {"error": str(e)}
    
    def _cache_contact(self, contact_id: str, name: str, email: str = None, 
                      phone: str = None, company_name: str = None):
        """Cache a single contact"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO crm_contacts_cache 
                        (contact_id, name, company_name, email, phone, last_sync, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (contact_id) 
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            company_name = EXCLUDED.company_name,
                            email = EXCLUDED.email,
                            phone = EXCLUDED.phone,
                            last_sync = EXCLUDED.last_sync
                    """, (contact_id, name, company_name, email, phone, datetime.now(), datetime.now()))
                conn.commit()
        except Exception as e:
            logger.error(f"Cache update failed: {e}")
            raise

# Global instance
crm_bridge = SimpleCRMBridge()

def health_check():
    """Simple health check"""
    try:
        stats = crm_bridge.get_cache_stats()
        return {
            "status": "healthy",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Test the bridge
    print("Testing CRM Bridge...")
    
    # Test health
    health = health_check()
    print(f"Health: {health}")
    
    # Test search
    contacts = crm_bridge.search_contacts(limit=5)
    print(f"Found {len(contacts)} contacts")
    
    # Test sync
    try:
        sync_result = crm_bridge.sync_all_contacts()
        print(f"Sync result: {sync_result}")
    except Exception as e:
        print(f"Sync failed: {e}")