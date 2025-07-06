#!/usr/bin/env python3
"""
CRM Sync Service - Automated background sync and manual triggers
"""

import os
import requests
import json
import threading
import time
import schedule
import logging
from datetime import datetime
from database.connection import SessionLocal
from database.models import CRMContactsCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LACRM Configuration
LACRM_API_KEY = os.getenv("CRM_API_KEY", "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W")
LACRM_BASE_URL = "https://api.lessannoyingcrm.com"

# Sync settings
SYNC_INTERVAL_HOURS = int(os.getenv("CRM_SYNC_INTERVAL_HOURS", "4"))  # Default: every 4 hours
ENABLE_AUTO_SYNC = os.getenv("ENABLE_AUTO_SYNC", "true").lower() == "true"

class CRMSyncService:
    """Background CRM sync service with scheduled and triggered syncing"""
    
    def __init__(self):
        self.is_running = False
        self.sync_thread = None
        self.last_sync_time = None
        self.sync_in_progress = False
        
    def sync_contacts_from_lacrm(self):
        """Sync all contacts from LACRM using pagination"""
        
        if self.sync_in_progress:
            logger.info("🔄 Sync already in progress, skipping...")
            return False
            
        self.sync_in_progress = True
        
        try:
            logger.info("🔄 Starting CRM sync from LACRM...")
            start_time = datetime.now()
            
            # Extract UserCode from API key
            user_code = LACRM_API_KEY.split('-')[0]
            
            # Use SearchContacts with proper pagination to get ALL contacts
            all_customers = {}  # Use dict to deduplicate by ContactId
            
            page = 1
            max_results_per_page = 10000  # LACRM API maximum
            total_retrieved = 0
            
            while True:
                logger.info(f"📄 Fetching page {page} (up to {max_results_per_page} records)...")
                
                params = {
                    'APIToken': LACRM_API_KEY,
                    'UserCode': user_code,
                    'Function': 'SearchContacts',
                    'SearchTerm': '',  # Empty to get all contacts
                    'MaxNumberOfResults': max_results_per_page,
                    'Page': page
                }
                
                try:
                    response = requests.get(LACRM_BASE_URL, params=params, timeout=30)
                    
                    if response.status_code != 200:
                        logger.error(f"❌ API error: {response.status_code}")
                        break
                    
                    result_data = json.loads(response.text)
                    
                    if not result_data.get('Success'):
                        logger.error(f"❌ CRM API failed: {result_data.get('Error', 'Unknown error')}")
                        break
                    
                    customers_data = result_data.get('Result', [])
                    
                    if not isinstance(customers_data, list):
                        customers_data = [customers_data] if customers_data else []
                    
                    # If we got no results, we've reached the end
                    if len(customers_data) == 0:
                        logger.info("📋 No more customers found - reached end of data")
                        break
                    
                    # Add to our deduplicated collection
                    new_customers = 0
                    for customer in customers_data:
                        contact_id = str(customer.get('ContactId', ''))
                        if contact_id and contact_id not in all_customers:
                            all_customers[contact_id] = customer
                            new_customers += 1
                    
                    total_retrieved += new_customers
                    logger.info(f"📊 Page {page}: {new_customers} new unique customers (Total: {len(all_customers)})")
                    
                    # Move to next page
                    page += 1
                    
                    # Safety check to prevent infinite loops
                    if page > 100:
                        logger.warning("⚠️ Safety limit reached - stopping pagination")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Page {page} fetch failed: {e}")
                    break
            
            # Convert back to list
            customers_list = list(all_customers.values())
            logger.info(f"🎉 Pagination complete! Found {len(customers_list)} unique customers")
            
            # Update database cache
            logger.info("💾 Updating database cache...")
            
            session = SessionLocal()
            
            # Clear existing cache
            logger.info("🧹 Clearing existing cache...")
            session.query(CRMContactsCache).delete()
            session.commit()
            
            # Insert all customers
            inserted_count = 0
            skipped_count = 0
            
            for customer in customers_list:
                try:
                    # Extract customer data using LACRM format
                    contact_id = str(customer.get('ContactId', ''))
                    
                    # Extract company name
                    company_name = str(customer.get('CompanyName', '') or '')
                    
                    # Extract name - prefer individual first/last name
                    name = company_name or 'Unknown Contact'  # Default to company name
                    first_name = ""
                    last_name = ""
                    
                    if isinstance(customer.get('Name'), dict):
                        name_obj = customer['Name']
                        first_name = name_obj.get('FirstName', '')
                        last_name = name_obj.get('LastName', '')
                        if first_name or last_name:
                            name = f"{first_name} {last_name}".strip()
                    elif customer.get('FirstName') or customer.get('LastName'):
                        first_name = customer.get('FirstName', '')
                        last_name = customer.get('LastName', '')
                        if first_name or last_name:
                            name = f"{first_name} {last_name}".strip()
                    
                    # Extract email (LACRM format: list of dicts with 'Text' field)
                    email = ""
                    email_raw = customer.get('Email', '')
                    if isinstance(email_raw, list) and len(email_raw) > 0:
                        first_email = email_raw[0]
                        if isinstance(first_email, dict):
                            email_text = first_email.get('Text', '')
                            email = email_text.split(' (')[0] if email_text else ''
                        else:
                            email = str(first_email)
                    elif isinstance(email_raw, dict):
                        email = str(email_raw.get('Text', '') or '')
                    else:
                        email = str(email_raw or '')
                    
                    # Extract phone (LACRM format: list of dicts with 'Text' field)
                    phone = ""
                    phone_raw = customer.get('Phone', '')
                    if isinstance(phone_raw, list) and len(phone_raw) > 0:
                        first_phone = phone_raw[0]
                        if isinstance(first_phone, dict):
                            phone_text = first_phone.get('Text', '')
                            phone = phone_text.split(' (')[0] if phone_text else ''
                        else:
                            phone = str(first_phone)
                    elif isinstance(phone_raw, dict):
                        phone = str(phone_raw.get('Text', '') or '')
                    else:
                        phone = str(phone_raw or '')
                    
                    # Extract address (LACRM format: list of dicts)
                    address_data = None
                    address_raw = customer.get('Address', '')
                    if isinstance(address_raw, list) and len(address_raw) > 0:
                        first_address = address_raw[0]
                        if isinstance(first_address, dict):
                            address_data = {
                                "street_address": first_address.get('Street', ''),
                                "city": first_address.get('City', ''),
                                "state": first_address.get('State', ''),
                                "zip_code": first_address.get('Zip', ''),
                                "country": first_address.get('Country', ''),
                                "type": first_address.get('Type', 'Work')
                            }
                    
                    # Skip if no essential data
                    if not contact_id:
                        skipped_count += 1
                        continue
                    
                    # Create cache entry
                    cache_entry = CRMContactsCache(
                        contact_id=contact_id,
                        name=name,
                        first_name=first_name,
                        last_name=last_name,
                        company_name=company_name,
                        email=email,
                        phone=phone,
                        address=address_data,
                        sync_status='synced',
                        last_sync=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(cache_entry)
                    inserted_count += 1
                    
                    # Commit in batches
                    if inserted_count % 100 == 0:
                        session.commit()
                        
                except Exception as e:
                    logger.error(f"⚠️ Error processing customer {customer.get('ContactId', 'unknown')}: {e}")
                    skipped_count += 1
                    continue
            
            # Final commit
            session.commit()
            session.close()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.last_sync_time = end_time
            
            logger.info(f"🎉 CRM Sync Complete!")
            logger.info(f"✅ Successfully cached: {inserted_count} customers")
            logger.info(f"⚠️ Skipped: {skipped_count} records")
            logger.info(f"⏱️ Duration: {duration.total_seconds():.1f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ CRM sync failed: {e}")
            return False
        finally:
            self.sync_in_progress = False
    
    def trigger_sync(self):
        """Trigger an immediate sync (non-blocking)"""
        if not self.sync_in_progress:
            logger.info("🔄 Triggering immediate CRM sync...")
            sync_thread = threading.Thread(target=self.sync_contacts_from_lacrm)
            sync_thread.daemon = True
            sync_thread.start()
        else:
            logger.info("⏳ Sync already in progress, skipping trigger")
    
    def start_background_scheduler(self):
        """Start the background sync scheduler"""
        if not ENABLE_AUTO_SYNC:
            logger.info("🚫 Auto-sync disabled via configuration")
            return
        
        if self.is_running:
            logger.info("⚠️ Background scheduler already running")
            return
        
        logger.info(f"🚀 Starting background CRM sync scheduler (every {SYNC_INTERVAL_HOURS} hours)")
        
        # Schedule periodic sync
        schedule.every(SYNC_INTERVAL_HOURS).hours.do(self.sync_contacts_from_lacrm)
        
        # Also schedule daily sync at 3 AM as backup
        schedule.every().day.at("03:00").do(self.sync_contacts_from_lacrm)
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=run_scheduler)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        logger.info("✅ Background sync scheduler started")
        
        # Run initial sync
        logger.info("🔄 Running initial sync...")
        self.trigger_sync()
    
    def stop_background_scheduler(self):
        """Stop the background sync scheduler"""
        if self.is_running:
            logger.info("🛑 Stopping background sync scheduler...")
            self.is_running = False
            if self.sync_thread:
                self.sync_thread.join(timeout=5)
            schedule.clear()
            logger.info("✅ Background sync scheduler stopped")
    
    def get_sync_status(self):
        """Get current sync status"""
        return {
            "is_running": self.is_running,
            "sync_in_progress": self.sync_in_progress,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "auto_sync_enabled": ENABLE_AUTO_SYNC,
            "sync_interval_hours": SYNC_INTERVAL_HOURS
        }

# Global sync service instance
sync_service = CRMSyncService()

def start_sync_service():
    """Start the global sync service"""
    sync_service.start_background_scheduler()

def stop_sync_service():
    """Stop the global sync service"""
    sync_service.stop_background_scheduler()

def trigger_sync():
    """Trigger immediate sync"""
    sync_service.trigger_sync()

def get_sync_status():
    """Get sync status"""
    return sync_service.get_sync_status()

if __name__ == "__main__":
    # Run as standalone service
    logger.info("🏢 BDE Sales Portal - CRM Sync Service")
    logger.info("=" * 50)
    
    try:
        start_sync_service()
        
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down sync service...")
        stop_sync_service()
        logger.info("✅ Sync service stopped")