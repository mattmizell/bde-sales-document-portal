#!/usr/bin/env python3
"""
BDE Sales Document Portal - Integrated Application
Complete portal with user management and document workflows
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Import configuration
from database.connection import engine, Base
from models.auth import User, UserSession
from models.core import Customer, DocumentTemplate, DocumentWorkflow, WorkflowEvent

# Import services
from services.auth_service import auth_service
from services.docuseal_service import DocuSealService

# Import API routes
from api_routes.auth_routes import router as auth_router
from api_routes.customer_routes import router as customer_router
from api_routes.workflow_routes import router as workflow_router
from api_routes.crm_routes import router as crm_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    
    # Startup
    logger.info("🚀 Starting BDE Sales Document Portal...")
    
    # Create database tables
    try:
        # Import all models to ensure they're registered
        from models.auth import Base as AuthBase
        from models.core import Base as CoreBase
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
        # Create default admin user if none exists
        from database.connection import get_db_context
        with get_db_context() as db:
            admin_exists = db.query(User).filter(User.role == "admin").first()
            if not admin_exists:
                logger.info("Creating default admin user...")
                admin = User(
                    username="admin",
                    email="admin@betterdayenergy.com",
                    first_name="System",
                    last_name="Administrator",
                    role="admin"
                )
                admin.set_password("changeme123")  # Change this!
                db.add(admin)
                db.commit()
                logger.info("✅ Default admin user created (username: admin, password: changeme123)")
        
        # Create default templates
        await create_default_templates()
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Test DocuSeal connection
    docuseal = DocuSealService(
        base_url=os.getenv('DOCUSEAL_SERVICE_URL', ''),
        api_token=os.getenv('DOCUSEAL_API_TOKEN', '')
    )
    
    health = await docuseal.health_check()
    if health["status"] == "healthy":
        logger.info(f"✅ DocuSeal connected: {health['templates_count']} templates available")
    else:
        logger.warning(f"⚠️ DocuSeal connection issue: {health}")
    
    logger.info("🎉 BDE Sales Document Portal ready!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down BDE Sales Document Portal...")

# Create FastAPI application
app = FastAPI(
    title="BDE Sales Document Portal",
    description="Integrated portal for document management and e-signatures",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://bde-sales-portal.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(workflow_router)
app.include_router(crm_router)

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - portal landing page"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BDE Sales Document Portal</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                padding: 3rem;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
            }
            h1 {
                color: #333;
                margin-bottom: 1rem;
            }
            p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 2rem;
            }
            .links {
                display: flex;
                gap: 1rem;
                justify-content: center;
                flex-wrap: wrap;
            }
            a {
                display: inline-block;
                padding: 0.75rem 1.5rem;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                transition: background 0.3s;
            }
            a:hover {
                background: #764ba2;
            }
            .status {
                margin-top: 2rem;
                padding: 1rem;
                background: #f0f4ff;
                border-radius: 6px;
                font-size: 0.875rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 BDE Sales Document Portal</h1>
            <p>
                Welcome to the Better Day Energy Sales Document Portal. 
                This integrated system manages customer documents, e-signatures, 
                and workflows for your sales team.
            </p>
            
            <div class="links">
                <a href="/app">Launch Portal</a>
                <a href="/api/docs">API Documentation</a>
                <a href="/health">System Health</a>
            </div>
            
            <div class="status">
                <strong>Status:</strong> Operational<br>
                <strong>Version:</strong> 2.0.0<br>
                <strong>Features:</strong> User Management, Customer Database, 
                Document Workflows, DocuSeal Integration
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    
    from database.connection import get_db_context
    
    # Test database
    try:
        with get_db_context() as db:
            user_count = db.query(User).count()
            customer_count = db.query(Customer).count()
            workflow_count = db.query(DocumentWorkflow).count()
            db_status = "healthy"
            db_stats = {
                "users": user_count,
                "customers": customer_count,
                "workflows": workflow_count
            }
    except Exception as e:
        db_status = f"error: {str(e)}"
        db_stats = {}
    
    # Test DocuSeal
    docuseal = DocuSealService(
        base_url=os.getenv('DOCUSEAL_SERVICE_URL', ''),
        api_token=os.getenv('DOCUSEAL_API_TOKEN', '')
    )
    docuseal_status = await docuseal.health_check()
    
    return {
        "status": "healthy" if db_status == "healthy" and docuseal_status.get("status") == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": {
                "status": db_status,
                "stats": db_stats
            },
            "docuseal": docuseal_status
        }
    }

async def create_default_templates():
    """Create default document templates"""
    
    from database.connection import get_db_context
    
    default_templates = [
        {
            "name": "Customer Setup Form",
            "document_type": "customer_setup",
            "description": "Initial customer onboarding and setup form",
            "docuseal_template_id": 1,  # Update with actual DocuSeal template ID
            "required_fields": ["company_name", "contact_name", "email", "phone"],
            "field_mappings": {
                "Company Name": "company_name",
                "Contact Name": "contact_name",
                "Email": "email",
                "Phone": "phone"
            }
        },
        {
            "name": "EFT Agreement",
            "document_type": "eft_agreement",
            "description": "Electronic Funds Transfer authorization agreement",
            "docuseal_template_id": 2,  # Update with actual DocuSeal template ID
            "required_fields": ["bank_name", "account_number", "routing_number"],
            "field_mappings": {
                "Bank Name": "bank_name",
                "Account Number": "account_number",
                "Routing Number": "routing_number"
            }
        },
        {
            "name": "VP Racing Fuels LOI",
            "document_type": "vp_racing_loi",
            "description": "Letter of Intent for VP Racing Fuels products",
            "docuseal_template_id": 3,  # Update with actual DocuSeal template ID
            "required_fields": ["annual_volume", "delivery_location", "start_date"],
            "field_mappings": {
                "Annual Volume": "annual_volume",
                "Delivery Location": "delivery_location",
                "Start Date": "start_date"
            }
        },
        {
            "name": "Phillips 66 LOI",
            "document_type": "p66_loi",
            "description": "Letter of Intent for Phillips 66 products",
            "docuseal_template_id": 4,  # Update with actual DocuSeal template ID
            "required_fields": ["annual_volume", "delivery_location", "start_date"],
            "field_mappings": {
                "Annual Volume": "annual_volume",
                "Delivery Location": "delivery_location",
                "Start Date": "start_date"
            }
        }
    ]
    
    try:
        with get_db_context() as db:
            for template_data in default_templates:
                # Check if template already exists
                existing = db.query(DocumentTemplate).filter(
                    DocumentTemplate.name == template_data["name"]
                ).first()
                
                if not existing:
                    template = DocumentTemplate(**template_data)
                    db.add(template)
                    logger.info(f"✅ Created template: {template_data['name']}")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"❌ Failed to create default templates: {e}")

# Mount static files if frontend directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Application runner
if __name__ == "__main__":
    uvicorn.run(
        "main_portal:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True if os.getenv("ENVIRONMENT") == "development" else False,
        log_level="info"
    )