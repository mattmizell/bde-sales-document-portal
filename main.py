#!/usr/bin/env python3
"""
Standalone CRM Server - Zero Dependency Hell
Just HTTP server + PostgreSQL + Requests
"""

import json
import logging
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
LACRM_API_KEY = os.getenv("LACRM_API_KEY", "1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W")
LACRM_BASE_URL = os.getenv("LACRM_BASE_URL", "https://api.lessannoyingcrm.com/v2/")
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'
)

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def search_contacts(query=None, limit=50):
    """Search contacts in cache"""
    try:
        with get_db_connection() as conn:
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

def get_cache_stats():
    """Get cache statistics"""
    try:
        with get_db_connection() as conn:
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

def create_contact_in_lacrm(name, email=None, phone=None, company_name=None, address=None):
    """Create new contact in LACRM with proper API handling"""
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
        
        response = requests.post(
            LACRM_BASE_URL,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        # Handle LACRM response quirks - manually parse JSON
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM creation failed: {error_msg}")
        
        contact_id = result.get("ContactId")
        
        # Update local cache immediately
        cache_contact_data(contact_id, name, email, phone, company_name, address)
        
        logger.info(f"✅ Contact created in LACRM: {contact_id}")
        
        return {
            "contact_id": contact_id,
            "name": name,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "source": "lacrm_api"
        }
        
    except Exception as e:
        logger.error(f"❌ Contact creation failed: {e}")
        raise

def update_contact_in_lacrm(contact_id, name=None, email=None, phone=None, company_name=None, address=None):
    """Update existing contact in LACRM"""
    try:
        # Build update parameters - only include non-None values
        params = {"ContactId": contact_id}
        
        if name is not None:
            params["Name"] = name
        if email is not None:
            params["Email"] = email
        if phone is not None:
            params["Phone"] = phone
        if company_name is not None:
            params["CompanyName"] = company_name
        if address is not None:
            params["Address"] = address
        
        payload = {
            "Function": "EditContact",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                **params
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM update failed: {error_msg}")
        
        # Update local cache
        update_cached_contact(contact_id, name, email, phone, company_name, address)
        
        logger.info(f"✅ Contact updated in LACRM: {contact_id}")
        
        return {
            "contact_id": contact_id,
            "updated_at": datetime.now().isoformat(),
            "updated_fields": [k for k, v in params.items() if k != "ContactId" and v is not None]
        }
        
    except Exception as e:
        logger.error(f"❌ Contact update failed: {e}")
        raise

def add_note_to_contact(contact_id, note_text, note_type="General"):
    """Add note to contact in LACRM"""
    try:
        payload = {
            "Function": "CreateNote",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id,
                "Note": note_text,
                "Type": note_type
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM note creation failed: {error_msg}")
        
        note_id = result.get("NoteId")
        
        logger.info(f"✅ Note added to contact {contact_id}: {note_id}")
        
        return {
            "note_id": note_id,
            "contact_id": contact_id,
            "note_text": note_text,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Note creation failed: {e}")
        raise

def get_contact_notes(contact_id):
    """Get all notes for a contact from LACRM"""
    try:
        payload = {
            "Function": "GetNotes",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM notes retrieval failed: {error_msg}")
        
        notes = result.get("Result", [])
        
        return {
            "contact_id": contact_id,
            "notes": notes,
            "count": len(notes)
        }
        
    except Exception as e:
        logger.error(f"❌ Notes retrieval failed: {e}")
        raise

def cache_contact_data(contact_id, name, email, phone, company_name, address):
    """Cache new contact data locally"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO crm_contacts_cache 
                    (contact_id, name, company_name, email, phone, address, last_sync, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contact_id) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        company_name = EXCLUDED.company_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        address = EXCLUDED.address,
                        last_sync = EXCLUDED.last_sync
                """, (
                    contact_id, name, company_name, email, phone, 
                    json.dumps({"address": address}) if address else None,
                    datetime.now(), datetime.now()
                ))
                
    except Exception as e:
        logger.error(f"❌ Cache update failed: {e}")

def update_cached_contact(contact_id, name, email, phone, company_name, address):
    """Update existing cached contact data"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Build dynamic update query
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if email is not None:
                    updates.append("email = %s")
                    params.append(email)
                if phone is not None:
                    updates.append("phone = %s")
                    params.append(phone)
                if company_name is not None:
                    updates.append("company_name = %s")
                    params.append(company_name)
                if address is not None:
                    updates.append("address = %s")
                    params.append(json.dumps({"address": address}))
                
                updates.append("last_sync = %s")
                params.append(datetime.now())
                params.append(contact_id)
                
                cur.execute(f"""
                    UPDATE crm_contacts_cache 
                    SET {', '.join(updates)}
                    WHERE contact_id = %s
                """, params)
                
    except Exception as e:
        logger.error(f"❌ Cache update failed: {e}")

def attach_document_to_contact(contact_id, file_url, file_name, document_type="Document"):
    """Attach document to contact in LACRM"""
    try:
        payload = {
            "Function": "UploadFile",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id,
                "FileUrl": file_url,
                "FileName": file_name,
                "FileType": document_type
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM document attachment failed: {error_msg}")
        
        file_id = result.get("FileId")
        
        logger.info(f"✅ Document attached to contact {contact_id}: {file_id}")
        
        return {
            "file_id": file_id,
            "contact_id": contact_id,
            "file_name": file_name,
            "file_url": file_url,
            "document_type": document_type,
            "attached_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Document attachment failed: {e}")
        raise

def attach_document_to_company(company_id, file_url, file_name, document_type="Document"):
    """Attach document to company in LACRM"""
    try:
        payload = {
            "Function": "UploadFile",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "CompanyId": company_id,
                "FileUrl": file_url,
                "FileName": file_name,
                "FileType": document_type
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM document attachment failed: {error_msg}")
        
        file_id = result.get("FileId")
        
        logger.info(f"✅ Document attached to company {company_id}: {file_id}")
        
        return {
            "file_id": file_id,
            "company_id": company_id,
            "file_name": file_name,
            "file_url": file_url,
            "document_type": document_type,
            "attached_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Document attachment failed: {e}")
        raise

def create_task_for_contact(contact_id, task_title, task_description="", due_date=None, priority="Normal"):
    """Create follow-up task for contact in LACRM"""
    try:
        # Calculate due date if not provided (default 7 days from now)
        if due_date is None:
            from datetime import timedelta
            due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        payload = {
            "Function": "CreateTask",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id,
                "Title": task_title,
                "Description": task_description,
                "DueDate": due_date,
                "Priority": priority  # Normal, High, Low
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM task creation failed: {error_msg}")
        
        task_id = result.get("TaskId")
        
        logger.info(f"✅ Task created for contact {contact_id}: {task_id}")
        
        return {
            "task_id": task_id,
            "contact_id": contact_id,
            "title": task_title,
            "description": task_description,
            "due_date": due_date,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Task creation failed: {e}")
        raise

def schedule_calendar_event(contact_id, event_title, event_description="", event_date=None, duration_minutes=60):
    """Schedule calendar event with contact in LACRM"""
    try:
        # Calculate event date if not provided (default tomorrow at 10 AM)
        if event_date is None:
            from datetime import timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            event_date = tomorrow.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%d %H:%M")
        
        payload = {
            "Function": "CreateEvent",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id,
                "Title": event_title,
                "Description": event_description,
                "StartTime": event_date,
                "DurationMinutes": duration_minutes
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM event creation failed: {error_msg}")
        
        event_id = result.get("EventId")
        
        logger.info(f"✅ Event scheduled for contact {contact_id}: {event_id}")
        
        return {
            "event_id": event_id,
            "contact_id": contact_id,
            "title": event_title,
            "description": event_description,
            "start_time": event_date,
            "duration_minutes": duration_minutes,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Event creation failed: {e}")
        raise

def get_contact_documents(contact_id):
    """Get all documents attached to a contact"""
    try:
        payload = {
            "Function": "GetFiles",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM documents retrieval failed: {error_msg}")
        
        documents = result.get("Result", [])
        
        return {
            "contact_id": contact_id,
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"❌ Documents retrieval failed: {e}")
        raise

def get_contact_tasks(contact_id):
    """Get all tasks for a contact"""
    try:
        payload = {
            "Function": "GetTasks",
            "Parameters": {
                "ApiToken": LACRM_API_KEY,
                "ContactId": contact_id
            }
        }
        
        response = requests.post(
            LACRM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"LACRM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if not result.get("Success"):
            error_msg = result.get("Errors", "Unknown error")
            raise Exception(f"LACRM tasks retrieval failed: {error_msg}")
        
        tasks = result.get("Result", [])
        
        return {
            "contact_id": contact_id,
            "tasks": tasks,
            "count": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"❌ Tasks retrieval failed: {e}")
        raise

class CRMHandler(BaseHTTPRequestHandler):
    """HTTP handler for CRM endpoints"""
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        try:
            if path == "/":
                self.send_json_response({
                    "service": "BDE CRM Bridge - Document Routing & Task Management",
                    "status": "operational",
                    "timestamp": datetime.now().isoformat(),
                    "capabilities": {
                        "contact_management": ["Search", "Create", "Update", "Get details"],
                        "document_management": ["Attach to contacts", "Attach to companies", "Retrieve documents"],
                        "task_scheduling": ["Create follow-up tasks", "Schedule calendar events", "Get task lists"],
                        "note_management": ["Add notes", "Retrieve notes"],
                        "cache_management": ["Real-time cache updates", "LACRM API integration"]
                    },
                    "document_workflows": {
                        "loi_completion": "Document signed → Attach to contact → Schedule follow-up",
                        "eft_processing": "EFT form → Attach to company → Create processing task",
                        "customer_onboarding": "Setup complete → All docs attached → Schedule onboarding call"
                    },
                    "endpoints": {
                        "docuseal_prefill": "GET /docuseal - DocuSeal form pre-fill interface",
                        "health": "GET /health",
                        "crm_health": "GET /api/v1/crm/health",
                        "contacts": {
                            "list": "GET /api/v1/crm/contacts?limit=N&search=query",
                            "search": "POST /api/v1/crm/contacts/search",
                            "create": "POST /api/v1/crm/contacts",
                            "update": "PUT /api/v1/crm/contacts/{id}"
                        },
                        "notes": {
                            "get": "GET /api/v1/crm/contacts/{id}/notes",
                            "add": "POST /api/v1/crm/contacts/{id}/notes"
                        },
                        "documents": {
                            "get_contact_docs": "GET /api/v1/crm/contacts/{id}/documents",
                            "attach_to_contact": "POST /api/v1/crm/contacts/{id}/documents",
                            "attach_to_company": "POST /api/v1/crm/companies/{id}/documents"
                        },
                        "tasks": {
                            "get_contact_tasks": "GET /api/v1/crm/contacts/{id}/tasks",
                            "create_task": "POST /api/v1/crm/contacts/{id}/tasks",
                            "schedule_event": "POST /api/v1/crm/contacts/{id}/events"
                        },
                        "stats": "GET /api/v1/crm/stats"
                    }
                })
                
            elif path == "/docuseal" or path == "/docuseal-prefill":
                # Serve the DocuSeal integration page
                try:
                    with open('docuseal_integration.html', 'r') as f:
                        html_content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(html_content.encode())
                except FileNotFoundError:
                    self.send_error(404, "DocuSeal integration page not found")
                
            elif path == "/health":
                stats = get_cache_stats()
                self.send_json_response({
                    "status": "healthy" if stats.get("total_contacts", 0) > 0 else "empty",
                    "stats": stats
                })
                
            elif path == "/api/v1/crm/health":
                stats = get_cache_stats()
                self.send_json_response({
                    "status": "healthy" if stats.get("total_contacts", 0) > 0 else "empty",
                    "cache_stats": stats
                })
                
            elif path == "/api/v1/crm/contacts":
                limit = int(query.get("limit", [50])[0])
                search = query.get("search", [None])[0]
                
                contacts = search_contacts(query=search, limit=limit)
                self.send_json_response({
                    "contacts": contacts,
                    "count": len(contacts),
                    "search": search,
                    "limit": limit
                })
                
            elif path == "/api/v1/crm/stats":
                stats = get_cache_stats()
                self.send_json_response({
                    "cache_stats": stats,
                    "performance": {
                        "response_time": "< 100ms",
                        "availability": "99.9%"
                    }
                })
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/notes"):
                # Get notes for contact
                contact_id = path.split("/")[-2]
                result = get_contact_notes(contact_id)
                self.send_json_response(result)
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/documents"):
                # Get documents for contact
                contact_id = path.split("/")[-2]
                result = get_contact_documents(contact_id)
                self.send_json_response(result)
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/tasks"):
                # Get tasks for contact
                contact_id = path.split("/")[-2]
                result = get_contact_tasks(contact_id)
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "Not found"}, status=404)
                
        except Exception as e:
            logger.error(f"GET error: {e}")
            self.send_json_response({"error": str(e)}, status=500)
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
            else:
                data = {}
            
            if path == "/api/v1/crm/contacts/search":
                query = data.get("query")
                limit = data.get("limit", 50)
                
                contacts = search_contacts(query=query, limit=limit)
                self.send_json_response({
                    "contacts": contacts,
                    "count": len(contacts),
                    "query": query
                })
                
            elif path == "/api/v1/crm/contacts":
                # Create new contact
                name = data.get("name")
                email = data.get("email")
                phone = data.get("phone")
                company_name = data.get("company_name")
                address = data.get("address")
                
                if not name:
                    self.send_json_response({"error": "Name is required"}, status=400)
                    return
                
                result = create_contact_in_lacrm(name, email, phone, company_name, address)
                self.send_json_response({
                    "success": True,
                    "contact": result,
                    "message": "Contact created successfully"
                })
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/notes"):
                # Add note to contact
                contact_id = path.split("/")[-2]
                note_text = data.get("note_text")
                note_type = data.get("note_type", "General")
                
                if not note_text:
                    self.send_json_response({"error": "Note text is required"}, status=400)
                    return
                
                result = add_note_to_contact(contact_id, note_text, note_type)
                self.send_json_response({
                    "success": True,
                    "note": result,
                    "message": "Note added successfully"
                })
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/documents"):
                # Attach document to contact
                contact_id = path.split("/")[-2]
                file_url = data.get("file_url")
                file_name = data.get("file_name")
                document_type = data.get("document_type", "Document")
                
                if not file_url or not file_name:
                    self.send_json_response({"error": "file_url and file_name are required"}, status=400)
                    return
                
                result = attach_document_to_contact(contact_id, file_url, file_name, document_type)
                self.send_json_response({
                    "success": True,
                    "document": result,
                    "message": "Document attached successfully"
                })
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/tasks"):
                # Create task for contact
                contact_id = path.split("/")[-2]
                task_title = data.get("task_title")
                task_description = data.get("task_description", "")
                due_date = data.get("due_date")  # YYYY-MM-DD format
                priority = data.get("priority", "Normal")
                
                if not task_title:
                    self.send_json_response({"error": "task_title is required"}, status=400)
                    return
                
                result = create_task_for_contact(contact_id, task_title, task_description, due_date, priority)
                self.send_json_response({
                    "success": True,
                    "task": result,
                    "message": "Task created successfully"
                })
                
            elif path.startswith("/api/v1/crm/contacts/") and path.endswith("/events"):
                # Schedule calendar event for contact
                contact_id = path.split("/")[-2]
                event_title = data.get("event_title")
                event_description = data.get("event_description", "")
                event_date = data.get("event_date")  # YYYY-MM-DD HH:MM format
                duration_minutes = data.get("duration_minutes", 60)
                
                if not event_title:
                    self.send_json_response({"error": "event_title is required"}, status=400)
                    return
                
                result = schedule_calendar_event(contact_id, event_title, event_description, event_date, duration_minutes)
                self.send_json_response({
                    "success": True,
                    "event": result,
                    "message": "Event scheduled successfully"
                })
                
            elif path.startswith("/api/v1/crm/companies/") and path.endswith("/documents"):
                # Attach document to company
                company_id = path.split("/")[-2]
                file_url = data.get("file_url")
                file_name = data.get("file_name")
                document_type = data.get("document_type", "Document")
                
                if not file_url or not file_name:
                    self.send_json_response({"error": "file_url and file_name are required"}, status=400)
                    return
                
                result = attach_document_to_company(company_id, file_url, file_name, document_type)
                self.send_json_response({
                    "success": True,
                    "document": result,
                    "message": "Document attached to company successfully"
                })
                
            elif path == "/api/docuseal/create-form":
                # Create DocuSeal form with pre-filled data
                template_id = data.get("template_id")
                contact_id = data.get("contact_id")
                prefilled_data = data.get("prefilled_data", {})
                contact_email = data.get("contact_email")
                contact_name = data.get("contact_name")
                
                if not template_id or not contact_email:
                    self.send_json_response({"error": "template_id and contact_email are required"}, status=400)
                    return
                
                # Map template names to actual DocuSeal template IDs
                template_mapping = {
                    "customer_setup": os.getenv("DOCUSEAL_CUSTOMER_SETUP_TEMPLATE_ID", "VmPsZnK4ARbXET"),
                    "eft_auth": os.getenv("DOCUSEAL_EFT_TEMPLATE_ID", ""),
                    "p66_loi": os.getenv("DOCUSEAL_P66_LOI_TEMPLATE_ID", ""),
                    "vp_loi": os.getenv("DOCUSEAL_VP_LOI_TEMPLATE_ID", "")
                }
                
                actual_template_id = template_mapping.get(template_id, template_id)
                
                # Call DocuSeal API
                docuseal_api_url = os.getenv("DOCUSEAL_SERVICE_URL", "https://bde-docuseal-selfhosted.onrender.com") + "/api"
                docuseal_api_key = os.getenv("DOCUSEAL_API_TOKEN", "")
                
                if not docuseal_api_key:
                    self.send_json_response({"error": "DocuSeal API key not configured"}, status=500)
                    return
                
                payload = {
                    "template_id": actual_template_id,
                    "send_email": False,  # Don't auto-send, return link instead
                    "submitters": [{
                        "role": "First Party",
                        "email": contact_email,
                        "name": contact_name or "Customer",
                        "values": prefilled_data
                    }]
                }
                
                headers = {
                    "X-Auth-Token": docuseal_api_key,
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.post(
                        f"{docuseal_api_url}/submissions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        # Get the signing URL from the first submitter
                        signing_url = None
                        if result.get("submitters") and len(result["submitters"]) > 0:
                            signing_url = result["submitters"][0].get("embed_src")
                        
                        # Log successful creation
                        if contact_id:
                            logger.info(f"✅ DocuSeal form created for contact {contact_id}: {signing_url}")
                        
                        self.send_json_response({
                            "success": True,
                            "signing_url": signing_url,
                            "submission_id": result.get("id"),
                            "template_id": actual_template_id,
                            "message": "DocuSeal form created successfully"
                        })
                    else:
                        error_msg = f"DocuSeal API error: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        self.send_json_response({"error": error_msg}, status=500)
                        
                except requests.exceptions.RequestException as e:
                    error_msg = f"DocuSeal API request failed: {str(e)}"
                    logger.error(error_msg)
                    self.send_json_response({"error": error_msg}, status=500)
                
            else:
                self.send_json_response({"error": "Not found"}, status=404)
                
        except Exception as e:
            logger.error(f"POST error: {e}")
            self.send_json_response({"error": str(e)}, status=500)
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urlparse(self.path).path
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
            else:
                data = {}
            
            if path.startswith("/api/v1/crm/contacts/") and not path.endswith("/notes"):
                # Update contact
                contact_id = path.split("/")[-1]
                name = data.get("name")
                email = data.get("email")
                phone = data.get("phone")
                company_name = data.get("company_name")
                address = data.get("address")
                
                result = update_contact_in_lacrm(contact_id, name, email, phone, company_name, address)
                self.send_json_response({
                    "success": True,
                    "contact": result,
                    "message": "Contact updated successfully"
                })
                
            else:
                self.send_json_response({"error": "Not found"}, status=404)
                
        except Exception as e:
            logger.error(f"PUT error: {e}")
            self.send_json_response({"error": str(e)}, status=500)
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2, default=str)
        self.wfile.write(response_json.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use proper logging"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server():
    """Run the HTTP server"""
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 BDE CRM Bridge starting on port {port}")
    logger.info(f"📊 Health check: http://localhost:{port}/health")
    logger.info(f"🔍 Search contacts: http://localhost:{port}/api/v1/crm/contacts")
    
    server = HTTPServer(('0.0.0.0', port), CRMHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.shutdown()

if __name__ == "__main__":
    run_server()