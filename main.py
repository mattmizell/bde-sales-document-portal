#!/usr/bin/env python3
"""
BDE Sales Document Portal - Main Application

Clean, modern document signing solution with DocuSeal integration.
No legacy canvas signature code - professional e-signatures from day one.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
import uvicorn

from database.connection import get_db_session
from services.docuseal_integration import DocuSealIntegration
from services.email_service import EmailService
from models.requests import (
    CustomerCreateRequest,
    DocumentInitiateRequest,
    WebhookEventRequest
)
from api_routes.crm_routes import router as crm_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BDE Sales Document Portal",
    description="Professional document signing with DocuSeal integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(crm_router)

# Static files for any frontend assets
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
docuseal_integration = DocuSealIntegration(
    service_url=os.getenv('DOCUSEAL_SERVICE_URL', 'http://localhost:8001')
)

email_service = EmailService(
    smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
    smtp_port=int(os.getenv('SMTP_PORT', '587')),
    smtp_username=os.getenv('SMTP_USERNAME', 'transaction.coordinator.agent@gmail.com'),
    smtp_password=os.getenv('SMTP_PASSWORD', 'xmvi xvso zblo oewe'),
    from_email=os.getenv('FROM_EMAIL', 'transaction.coordinator.agent@gmail.com')
)

# =====================================================
# HEALTH CHECK AND STATUS
# =====================================================

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "service": "BDE Sales Document Portal",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "description": "Professional document signing with DocuSeal integration"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    
    # Test database connection
    try:
        db = next(get_db_session())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Test DocuSeal connection
    docuseal_status = await docuseal_integration.health_check()
    
    # Test email service
    email_status = email_service.test_connection()
    
    return {
        "status": "healthy" if all([
            db_status == "healthy",
            docuseal_status.get("status") == "healthy",
            email_status.get("status") == "healthy"
        ]) else "degraded",
        "services": {
            "database": db_status,
            "docuseal": docuseal_status,
            "email": email_status
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# =====================================================
# DOCUMENT WORKFLOW ENDPOINTS
# =====================================================

@app.post("/api/v1/customers")
async def create_customer(
    customer_data: CustomerCreateRequest,
    db = Depends(get_db_session)
):
    """Create new customer record"""
    
    try:
        from database.models import Customer
        
        # Create customer in database
        customer = Customer(
            company_name=customer_data.company_name,
            contact_name=customer_data.contact_name,
            email=customer_data.email,
            phone=customer_data.phone,
            address=customer_data.address,
            city=customer_data.city,
            state=customer_data.state,
            zip_code=customer_data.zip_code
        )
        
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        logger.info(f"✅ Customer created: {customer.company_name} ({customer.id})")
        
        return {
            "id": str(customer.id),
            "company_name": customer.company_name,
            "email": customer.email,
            "created_at": customer.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Customer creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create customer: {str(e)}")

@app.post("/api/v1/documents/initiate")
async def initiate_document_signing(
    request_data: DocumentInitiateRequest,
    background_tasks: BackgroundTasks,
    db = Depends(get_db_session)
):
    """Initiate document signing workflow"""
    
    try:
        # Create DocuSeal submission via external service
        submission_result = await docuseal_integration.initiate_document(
            template_id=request_data.template_id,
            customer_email=request_data.customer_email,
            customer_name=request_data.customer_name,
            form_data=request_data.form_data
        )
        
        if not submission_result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=f"DocuSeal submission failed: {submission_result.get('error')}"
            )
        
        # Store workflow in database
        from database.models import DocumentWorkflow
        
        workflow = DocumentWorkflow(
            customer_id=request_data.customer_id,
            workflow_type=request_data.document_type,
            workflow_name=f"{request_data.document_type.upper()} - {request_data.customer_name}",
            docuseal_submission_id=submission_result["submission_id"],
            status="initiated",
            form_data=request_data.form_data,
            initiated_by=request_data.initiated_by,
            initiated_at=datetime.utcnow()
        )
        
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # Log event
        from database.models import WorkflowEvent
        event = WorkflowEvent(
            workflow_id=workflow.id,
            event_type="initiated",
            event_description=f"Document signing initiated by {request_data.initiated_by}",
            user_email=request_data.initiated_by
        )
        db.add(event)
        db.commit()
        
        logger.info(f"✅ Document workflow initiated: {workflow.id}")
        
        return {
            "workflow_id": str(workflow.id),
            "submission_id": submission_result["submission_id"],
            "signing_url": submission_result.get("signing_url"),
            "status": "initiated",
            "message": f"Document sent to {request_data.customer_email}"
        }
        
    except Exception as e:
        logger.error(f"❌ Document initiation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate document: {str(e)}")

# =====================================================
# WEBHOOK ENDPOINTS
# =====================================================

@app.post("/api/v1/webhooks/docuseal")
async def handle_docuseal_webhook(
    webhook_data: WebhookEventRequest,
    background_tasks: BackgroundTasks,
    db = Depends(get_db_session)
):
    """Handle DocuSeal webhook events"""
    
    try:
        logger.info(f"📥 DocuSeal webhook received: {webhook_data.event_type}")
        
        # Find workflow by submission ID
        from database.models import DocumentWorkflow, WorkflowEvent
        
        workflow = db.query(DocumentWorkflow).filter(
            DocumentWorkflow.docuseal_submission_id == webhook_data.submission_id
        ).first()
        
        if not workflow:
            logger.warning(f"⚠️ Workflow not found for submission: {webhook_data.submission_id}")
            return {"status": "workflow_not_found"}
        
        # Update workflow status based on event
        if webhook_data.event_type == "form.completed":
            workflow.status = "completed"
            workflow.completed_at = datetime.utcnow()
            workflow.completed_by = webhook_data.submitter_email
            workflow.document_url = webhook_data.document_url
            
            # Send completion notification
            background_tasks.add_task(
                send_completion_notification,
                workflow.id,
                workflow.initiated_by
            )
            
        elif webhook_data.event_type == "form.viewed":
            workflow.status = "viewed"
            
        elif webhook_data.event_type == "form.started":
            workflow.status = "in_progress"
        
        # Log event
        event = WorkflowEvent(
            workflow_id=workflow.id,
            event_type=webhook_data.event_type,
            event_description=f"DocuSeal event: {webhook_data.event_type}",
            event_data=webhook_data.dict(),
            user_email=webhook_data.submitter_email
        )
        
        db.add(event)
        db.commit()
        
        logger.info(f"✅ Webhook processed: {webhook_data.event_type} for workflow {workflow.id}")
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"❌ Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

# =====================================================
# DASHBOARD AND STATUS ENDPOINTS
# =====================================================

@app.get("/api/v1/workflows")
async def list_workflows(
    status: Optional[str] = None,
    limit: int = 50,
    db = Depends(get_db_session)
):
    """List document workflows with optional filtering"""
    
    try:
        from database.models import DocumentWorkflow
        
        query = db.query(DocumentWorkflow)
        
        if status:
            query = query.filter(DocumentWorkflow.status == status)
        
        workflows = query.order_by(DocumentWorkflow.created_at.desc()).limit(limit).all()
        
        return {
            "workflows": [
                {
                    "id": str(w.id),
                    "workflow_type": w.workflow_type,
                    "workflow_name": w.workflow_name,
                    "status": w.status,
                    "initiated_by": w.initiated_by,
                    "initiated_at": w.initiated_at.isoformat() if w.initiated_at else None,
                    "completed_at": w.completed_at.isoformat() if w.completed_at else None,
                    "document_url": w.document_url
                }
                for w in workflows
            ],
            "count": len(workflows)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")

@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow_details(
    workflow_id: str,
    db = Depends(get_db_session)
):
    """Get detailed workflow information"""
    
    try:
        from database.models import DocumentWorkflow, WorkflowEvent
        
        workflow = db.query(DocumentWorkflow).filter(
            DocumentWorkflow.id == workflow_id
        ).first()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Get events
        events = db.query(WorkflowEvent).filter(
            WorkflowEvent.workflow_id == workflow_id
        ).order_by(WorkflowEvent.timestamp.asc()).all()
        
        return {
            "workflow": {
                "id": str(workflow.id),
                "workflow_type": workflow.workflow_type,
                "workflow_name": workflow.workflow_name,
                "status": workflow.status,
                "form_data": workflow.form_data,
                "initiated_by": workflow.initiated_by,
                "initiated_at": workflow.initiated_at.isoformat() if workflow.initiated_at else None,
                "completed_by": workflow.completed_by,
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                "document_url": workflow.document_url,
                "docuseal_submission_id": workflow.docuseal_submission_id
            },
            "events": [
                {
                    "event_type": e.event_type,
                    "event_description": e.event_description,
                    "timestamp": e.timestamp.isoformat(),
                    "user_email": e.user_email
                }
                for e in events
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get workflow details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow details: {str(e)}")

# =====================================================
# BACKGROUND TASKS
# =====================================================

async def send_completion_notification(workflow_id: str, recipient_email: str):
    """Send notification when document is completed"""
    
    try:
        # Implementation for completion notification
        logger.info(f"📧 Sending completion notification for workflow {workflow_id} to {recipient_email}")
        
        # Could send email, Slack notification, etc.
        
    except Exception as e:
        logger.error(f"❌ Failed to send completion notification: {str(e)}")

# =====================================================
# APPLICATION STARTUP
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    
    logger.info("🚀 BDE Sales Document Portal starting up...")
    
    # Test connections
    health = await health_check()
    
    if health["status"] == "healthy":
        logger.info("✅ All services connected successfully")
    else:
        logger.warning("⚠️ Some services may not be available")
        logger.warning(f"Service status: {health['services']}")
    
    logger.info("🎉 BDE Sales Document Portal ready!")

if __name__ == "__main__":
    # Get port from environment (Render sets PORT)
    port = int(os.getenv("PORT", 8000))
    
    # For local development and production
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )