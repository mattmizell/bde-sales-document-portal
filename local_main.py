#!/usr/bin/env python3
"""
BDE Sales Document Portal - Local Development Version
Uses PostgreSQL database with relative paths for Render compatibility
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Set up relative paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Database URL for local development (external URL for testing)
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'
)

# Import database components
try:
    from sqlalchemy import create_engine, text, Column, String, DateTime, Integer, Text
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.pool import QueuePool
    print("✅ SQLAlchemy imports successful")
except ImportError as e:
    print(f"❌ SQLAlchemy import failed: {e}")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(10))
    zip_code = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentWorkflow(Base):
    __tablename__ = 'document_workflows'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    workflow_type = Column(String(100))
    workflow_name = Column(String(255))
    docuseal_submission_id = Column(String(255))
    status = Column(String(50), default='initiated')
    form_data = Column(Text)
    initiated_by = Column(String(255))
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    completed_by = Column(String(255))
    document_url = Column(Text)

def create_database_connection():
    """Create database engine and session"""
    try:
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=True  # Show SQL queries for debugging
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        print("✅ Database tables created/verified")
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, SessionLocal
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None, None

def create_simple_web_server():
    """Create a simple HTTP server for local testing"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    # Initialize database
    engine, SessionLocal = create_database_connection()
    
    if not engine:
        print("❌ Cannot start server without database connection")
        return
    
    class PortalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.serve_dashboard()
            elif self.path == '/health':
                self.serve_health()
            elif self.path == '/api/customers':
                self.serve_customers()
            elif self.path == '/api/workflows':
                self.serve_workflows()
            else:
                self.send_error(404)
        
        def do_POST(self):
            if self.path == '/api/customers':
                self.create_customer()
            elif self.path == '/api/workflows':
                self.create_workflow()
            else:
                self.send_error(404)
        
        def serve_dashboard(self):
            """Serve main dashboard HTML"""
            html = '''
<!DOCTYPE html>
<html>
<head>
    <title>BDE Sales Document Portal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #007cba; color: white; padding: 20px; margin: -20px -20px 20px -20px; border-radius: 10px 10px 0 0; }
        .section { margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }
        .form-row { display: flex; gap: 10px; margin: 10px 0; }
        input, select, button { padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        input, select { flex: 1; }
        button { background: #007cba; color: white; border: none; cursor: pointer; min-width: 120px; }
        button:hover { background: #005a87; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .status-card { background: white; padding: 15px; border-radius: 5px; border-left: 4px solid #007cba; }
        .success { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 BDE Sales Document Portal</h1>
            <p>PostgreSQL-powered document management with DocuSeal integration</p>
        </div>
        
        <div class="section">
            <h2>📋 Create Customer</h2>
            <form id="customerForm">
                <div class="form-row">
                    <input type="text" id="companyName" placeholder="Company Name" required>
                    <input type="text" id="contactName" placeholder="Contact Name" required>
                </div>
                <div class="form-row">
                    <input type="email" id="email" placeholder="Email Address" required>
                    <input type="tel" id="phone" placeholder="Phone Number">
                </div>
                <div class="form-row">
                    <input type="text" id="address" placeholder="Street Address">
                    <input type="text" id="city" placeholder="City">
                    <input type="text" id="state" placeholder="State" maxlength="2">
                    <input type="text" id="zipCode" placeholder="ZIP Code">
                </div>
                <button type="submit">Create Customer</button>
            </form>
            <div id="customerResult"></div>
        </div>
        
        <div class="section">
            <h2>📄 Start Document Workflow</h2>
            <form id="workflowForm">
                <div class="form-row">
                    <select id="workflowType" required>
                        <option value="">Select Document Type</option>
                        <option value="phillips66_loi">Phillips 66 Letter of Intent</option>
                        <option value="vp_racing_loi">VP Racing Fuels LOI</option>
                        <option value="eft_form">EFT Setup Form</option>
                        <option value="customer_setup">Customer Setup Document</option>
                    </select>
                    <input type="text" id="customerEmail" placeholder="Customer Email" required>
                </div>
                <button type="submit">Start Workflow</button>
            </form>
            <div id="workflowResult"></div>
        </div>
        
        <div class="section">
            <h2>📊 System Status</h2>
            <div class="status-grid">
                <div class="status-card">
                    <h3>Database</h3>
                    <div id="dbStatus">Checking...</div>
                </div>
                <div class="status-card">
                    <h3>Customers</h3>
                    <div id="customerCount">Loading...</div>
                </div>
                <div class="status-card">
                    <h3>Workflows</h3>
                    <div id="workflowCount">Loading...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function checkHealth() {
            try {
                const response = await fetch('/health');
                const health = await response.json();
                document.getElementById('dbStatus').innerHTML = 
                    health.database === 'connected' ? '<span class="success">✅ Connected</span>' : '<span class="error">❌ Disconnected</span>';
            } catch (e) {
                document.getElementById('dbStatus').innerHTML = '<span class="error">❌ Error</span>';
            }
        }
        
        async function loadCounts() {
            try {
                const customers = await fetch('/api/customers');
                const customerData = await customers.json();
                document.getElementById('customerCount').innerHTML = `${customerData.length} customers`;
                
                const workflows = await fetch('/api/workflows');
                const workflowData = await workflows.json();
                document.getElementById('workflowCount').innerHTML = `${workflowData.length} workflows`;
            } catch (e) {
                document.getElementById('customerCount').innerHTML = 'Error loading';
                document.getElementById('workflowCount').innerHTML = 'Error loading';
            }
        }
        
        document.getElementById('customerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                company_name: document.getElementById('companyName').value,
                contact_name: document.getElementById('contactName').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                address: document.getElementById('address').value,
                city: document.getElementById('city').value,
                state: document.getElementById('state').value,
                zip_code: document.getElementById('zipCode').value
            };
            
            try {
                const response = await fetch('/api/customers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('customerResult').innerHTML = '<span class="success">✅ Customer created successfully!</span>';
                    document.getElementById('customerForm').reset();
                    loadCounts();
                } else {
                    document.getElementById('customerResult').innerHTML = `<span class="error">❌ Error: ${result.error}</span>`;
                }
            } catch (e) {
                document.getElementById('customerResult').innerHTML = '<span class="error">❌ Network error</span>';
            }
        });
        
        document.getElementById('workflowForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                workflow_type: document.getElementById('workflowType').value,
                customer_email: document.getElementById('customerEmail').value,
                initiated_by: 'admin@bde.com'
            };
            
            try {
                const response = await fetch('/api/workflows', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('workflowResult').innerHTML = '<span class="success">✅ Workflow started successfully!</span>';
                    document.getElementById('workflowForm').reset();
                    loadCounts();
                } else {
                    document.getElementById('workflowResult').innerHTML = `<span class="error">❌ Error: ${result.error}</span>`;
                }
            } catch (e) {
                document.getElementById('workflowResult').innerHTML = '<span class="error">❌ Network error</span>';
            }
        });
        
        // Load initial data
        checkHealth();
        loadCounts();
        
        // Refresh every 30 seconds
        setInterval(() => {
            checkHealth();
            loadCounts();
        }, 30000);
    </script>
</body>
</html>
            '''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        
        def serve_health(self):
            """Health check endpoint"""
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                health = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'database': 'connected',
                    'database_url': DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'
                }
            except Exception as e:
                health = {
                    'status': 'unhealthy',
                    'timestamp': datetime.now().isoformat(),
                    'database': 'disconnected',
                    'error': str(e)
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health).encode())
        
        def serve_customers(self):
            """Get all customers"""
            try:
                session = SessionLocal()
                customers = session.query(Customer).all()
                
                customer_list = []
                for c in customers:
                    customer_list.append({
                        'id': c.id,
                        'company_name': c.company_name,
                        'contact_name': c.contact_name,
                        'email': c.email,
                        'phone': c.phone,
                        'created_at': c.created_at.isoformat() if c.created_at else None
                    })
                
                session.close()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(customer_list).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        def serve_workflows(self):
            """Get all workflows"""
            try:
                session = SessionLocal()
                workflows = session.query(DocumentWorkflow).all()
                
                workflow_list = []
                for w in workflows:
                    workflow_list.append({
                        'id': w.id,
                        'workflow_type': w.workflow_type,
                        'workflow_name': w.workflow_name,
                        'status': w.status,
                        'initiated_by': w.initiated_by,
                        'initiated_at': w.initiated_at.isoformat() if w.initiated_at else None
                    })
                
                session.close()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(workflow_list).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        def create_customer(self):
            """Create new customer"""
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
                
                session = SessionLocal()
                
                customer = Customer(
                    company_name=data['company_name'],
                    contact_name=data.get('contact_name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    address=data.get('address'),
                    city=data.get('city'),
                    state=data.get('state'),
                    zip_code=data.get('zip_code')
                )
                
                session.add(customer)
                session.commit()
                session.refresh(customer)
                
                result = {
                    'success': True,
                    'id': customer.id,
                    'company_name': customer.company_name
                }
                
                session.close()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
        
        def create_workflow(self):
            """Create new workflow"""
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
                
                session = SessionLocal()
                
                workflow = DocumentWorkflow(
                    workflow_type=data['workflow_type'],
                    workflow_name=f"{data['workflow_type'].upper()} - {data.get('customer_email', 'Unknown')}",
                    docuseal_submission_id=f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    status='initiated',
                    form_data=json.dumps(data),
                    initiated_by=data.get('initiated_by', 'system')
                )
                
                session.add(workflow)
                session.commit()
                session.refresh(workflow)
                
                result = {
                    'success': True,
                    'workflow_id': workflow.id,
                    'workflow_type': workflow.workflow_type,
                    'status': workflow.status
                }
                
                session.close()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
    
    # Start server
    PORT = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', PORT), PortalHandler)
    print(f"🚀 BDE Document Portal starting on port {PORT}")
    print(f"📊 Dashboard: http://localhost:{PORT}")
    print(f"🗄️ Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print(f"📁 Base directory: {BASE_DIR}")
    
    server.serve_forever()

if __name__ == '__main__':
    create_simple_web_server()