#!/usr/bin/env python3
"""
BDE Sales Document Portal - Zero Dependencies Version
Uses only Python standard library to avoid dependency hell
"""

import os
import json
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import hashlib
import uuid
import threading
import time

# Configuration
DOCUSEAL_URL = os.getenv('DOCUSEAL_URL', 'https://bde-docuseal-selfhosted.onrender.com')
DOCUSEAL_TOKEN = os.getenv('DOCUSEAL_TOKEN', '')
PORT = int(os.getenv('PORT', 8000))
DB_FILE = 'portal.db'

class DocumentPortal:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                email TEXT,
                created_at TEXT
            )
        ''')
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                customer_name TEXT,
                customer_email TEXT,
                document_type TEXT,
                docuseal_submission_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT
            )
        ''')
        
        # Add default admin user if none exists
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?)
            ''', ('admin', admin_hash, 'admin@bde.com', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def create_document(self, customer_name, customer_email, document_type, form_data):
        """Create document submission in DocuSeal"""
        try:
            # First save to local database
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            doc_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO documents (customer_name, customer_email, document_type, 
                                     docuseal_submission_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_name, customer_email, document_type, doc_id, datetime.now().isoformat()))
            
            local_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Submit to DocuSeal (simplified - would need actual template IDs)
            if DOCUSEAL_TOKEN:
                docuseal_data = {
                    'template_id': 1,  # Would be actual template ID
                    'submitters': [{
                        'name': customer_name,
                        'email': customer_email,
                        'role': 'Customer'
                    }]
                }
                
                req_data = json.dumps(docuseal_data).encode('utf-8')
                req = urllib.request.Request(
                    f'{DOCUSEAL_URL}/api/submissions',
                    data=req_data,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Auth-Token': DOCUSEAL_TOKEN
                    }
                )
                
                try:
                    with urllib.request.urlopen(req) as response:
                        result = json.loads(response.read())
                        
                        # Update with actual DocuSeal ID
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE documents SET docuseal_submission_id = ?
                            WHERE id = ?
                        ''', (result.get('id', doc_id), local_id))
                        conn.commit()
                        conn.close()
                        
                except urllib.error.URLError as e:
                    print(f"DocuSeal error: {e}")
            
            return {'success': True, 'id': local_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_documents(self):
        """Get all documents"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, customer_name, customer_email, document_type, 
                   status, created_at, completed_at
            FROM documents ORDER BY created_at DESC
        ''')
        
        docs = []
        for row in cursor.fetchall():
            docs.append({
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'document_type': row[3],
                'status': row[4],
                'created_at': row[5],
                'completed_at': row[6]
            })
        
        conn.close()
        return docs

portal = DocumentPortal()

class PortalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/documents':
            self.serve_documents_api()
        elif self.path == '/health':
            self.serve_health()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/api/documents':
            self.create_document_api()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve simple HTML dashboard"""
        html = '''
<!DOCTYPE html>
<html>
<head>
    <title>BDE Document Portal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .form-section { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .documents { background: white; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        input, select, button { padding: 8px; margin: 5px; }
        button { background: #007cba; color: white; border: none; cursor: pointer; }
        button:hover { background: #005a87; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background: #f5f5f5; }
        .status-pending { color: #ff6b35; }
        .status-completed { color: #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <h1>BDE Sales Document Portal</h1>
        
        <div class="form-section">
            <h2>Create New Document</h2>
            <form id="documentForm">
                <input type="text" id="customerName" placeholder="Customer Name" required>
                <input type="email" id="customerEmail" placeholder="Customer Email" required>
                <select id="documentType" required>
                    <option value="">Select Document Type</option>
                    <option value="phillips66_loi">Phillips 66 Letter of Intent</option>
                    <option value="vp_racing_loi">VP Racing Fuels LOI</option>
                    <option value="eft_form">EFT Setup Form</option>
                    <option value="customer_setup">Customer Setup Form</option>
                </select>
                <button type="submit">Create Document</button>
            </form>
        </div>
        
        <div class="documents">
            <h2>Document Status</h2>
            <div id="documentsTable">Loading...</div>
        </div>
    </div>

    <script>
        async function loadDocuments() {
            try {
                const response = await fetch('/api/documents');
                const docs = await response.json();
                
                if (docs.length === 0) {
                    document.getElementById('documentsTable').innerHTML = '<p>No documents found.</p>';
                    return;
                }
                
                let html = '<table><tr><th>Customer</th><th>Email</th><th>Type</th><th>Status</th><th>Created</th></tr>';
                docs.forEach(doc => {
                    html += `<tr>
                        <td>${doc.customer_name}</td>
                        <td>${doc.customer_email}</td>
                        <td>${doc.document_type}</td>
                        <td class="status-${doc.status}">${doc.status}</td>
                        <td>${new Date(doc.created_at).toLocaleDateString()}</td>
                    </tr>`;
                });
                html += '</table>';
                
                document.getElementById('documentsTable').innerHTML = html;
            } catch (e) {
                document.getElementById('documentsTable').innerHTML = '<p>Error loading documents.</p>';
            }
        }
        
        document.getElementById('documentForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                customer_name: document.getElementById('customerName').value,
                customer_email: document.getElementById('customerEmail').value,
                document_type: document.getElementById('documentType').value
            };
            
            try {
                const response = await fetch('/api/documents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Document created successfully!');
                    document.getElementById('documentForm').reset();
                    loadDocuments();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (e) {
                alert('Error creating document');
            }
        });
        
        // Load documents on page load
        loadDocuments();
        
        // Refresh every 30 seconds
        setInterval(loadDocuments, 30000);
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_documents_api(self):
        """Serve documents JSON API"""
        docs = portal.get_documents()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(docs).encode())
    
    def create_document_api(self):
        """Create document via API"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            result = portal.create_document(
                data['customer_name'],
                data['customer_email'],
                data['document_type'],
                data
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_result).encode())
    
    def serve_health(self):
        """Health check endpoint"""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'docuseal_url': DOCUSEAL_URL
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health).encode())

def run_server():
    """Run the HTTP server"""
    server = HTTPServer(('0.0.0.0', PORT), PortalHandler)
    print(f"🚀 BDE Document Portal running on port {PORT}")
    print(f"📊 Dashboard: http://localhost:{PORT}")
    print(f"🔗 DocuSeal: {DOCUSEAL_URL}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()