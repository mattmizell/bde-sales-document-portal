"""
Document Workflow API Routes
Handle document creation, tracking, and management
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db_session
from services.auth_service import get_current_user
from services.docuseal_service import DocuSealService
from models.auth import User
from models.core import (
    Customer, DocumentTemplate, DocumentWorkflow, 
    WorkflowEvent, WorkflowStatus, DocumentType
)

router = APIRouter(prefix="/api/v1/workflows", tags=["Document Workflows"])

# Initialize DocuSeal service
docuseal_service = DocuSealService(
    base_url=os.getenv('DOCUSEAL_SERVICE_URL', 'https://bde-docuseal-selfhosted.onrender.com'),
    api_token=os.getenv('DOCUSEAL_API_TOKEN', '')
)

# Request/Response models
class WorkflowInitiateRequest(BaseModel):
    customer_id: int
    template_id: int
    form_data: Dict[str, Any] = {}
    notes: Optional[str] = None
    auto_send: bool = True

class TemplateCreateRequest(BaseModel):
    name: str
    document_type: DocumentType
    docuseal_template_id: int
    description: Optional[str] = None
    required_fields: List[str] = []
    field_mappings: Dict[str, str] = {}
    default_values: Dict[str, Any] = {}
    auto_send: bool = True
    expiry_days: int = 30
    reminder_days: int = 7

@router.post("/templates")
async def create_template(
    template_data: TemplateCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create document template configuration"""
    
    # Check if template already exists
    existing = db.query(DocumentTemplate).filter(
        DocumentTemplate.docuseal_template_id == template_data.docuseal_template_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Template with this DocuSeal ID already exists"
        )
    
    # Create template
    template = DocumentTemplate(
        **template_data.dict(),
        created_by_id=current_user.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "success": True,
        "template": template.to_dict()
    }

@router.get("/templates")
async def list_templates(
    document_type: Optional[DocumentType] = None,
    is_active: bool = True,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """List available document templates"""
    
    query = db.query(DocumentTemplate).filter(
        DocumentTemplate.is_active == is_active
    )
    
    if document_type:
        query = query.filter(DocumentTemplate.document_type == document_type)
    
    templates = query.all()
    
    # Also get templates from DocuSeal
    docuseal_templates = await docuseal_service.list_templates()
    
    return {
        "templates": [t.to_dict() for t in templates],
        "docuseal_templates": docuseal_templates,
        "total": len(templates)
    }

@router.post("/initiate")
async def initiate_workflow(
    request_data: WorkflowInitiateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Initiate new document workflow"""
    
    # Get customer
    customer = db.query(Customer).filter(
        Customer.id == request_data.customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get template
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == request_data.template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Create workflow
    workflow = DocumentWorkflow(
        customer_id=customer.id,
        template_id=template.id,
        initiated_by_id=current_user.id,
        workflow_name=f"{template.name} - {customer.company_name}",
        workflow_type=template.document_type,
        docuseal_template_id=template.docuseal_template_id,
        status=WorkflowStatus.INITIATED,
        form_data=request_data.form_data,
        notes=request_data.notes,
        initiated_at=datetime.utcnow()
    )
    
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # Log initiation event
    event = WorkflowEvent(
        workflow_id=workflow.id,
        event_type="workflow_initiated",
        event_description=f"Workflow initiated by {current_user.get_full_name()}",
        user_id=current_user.id,
        user_email=current_user.email
    )
    db.add(event)
    db.commit()
    
    # Send to DocuSeal if auto_send is enabled
    if request_data.auto_send and template.auto_send:
        # Merge form data with template defaults
        form_data = {**template.default_values, **request_data.form_data}
        
        # Apply field mappings
        if template.field_mappings:
            mapped_data = {}
            for docuseal_field, form_field in template.field_mappings.items():
                if form_field in form_data:
                    mapped_data[docuseal_field] = form_data[form_field]
            form_data = {**form_data, **mapped_data}
        
        # Send to DocuSeal
        result = await docuseal_service.create_submission(
            db=db,
            workflow=workflow,
            customer_email=customer.email,
            customer_name=customer.contact_name,
            form_data=form_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send document: {result['error']}"
            )
    
    return {
        "success": True,
        "workflow": workflow.to_dict(),
        "message": "Document workflow initiated successfully"
    }

@router.get("/")
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    customer_id: Optional[int] = None,
    document_type: Optional[DocumentType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """List workflows with filters"""
    
    query = db.query(DocumentWorkflow)
    
    # Apply filters based on user role
    if current_user.role == "user":
        # Regular users only see their own workflows
        query = query.filter(DocumentWorkflow.initiated_by_id == current_user.id)
    
    # Status filter
    if status:
        query = query.filter(DocumentWorkflow.status == status)
    
    # Customer filter
    if customer_id:
        query = query.filter(DocumentWorkflow.customer_id == customer_id)
    
    # Document type filter
    if document_type:
        query = query.filter(DocumentWorkflow.workflow_type == document_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    workflows = query.order_by(
        DocumentWorkflow.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "workflows": [w.to_dict() for w in workflows],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get workflow details"""
    
    workflow = db.query(DocumentWorkflow).filter(
        DocumentWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Check permissions
    if current_user.role == "user" and workflow.initiated_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Include related data
    workflow_dict = workflow.to_dict()
    workflow_dict["customer"] = workflow.customer.to_dict()
    workflow_dict["template"] = workflow.template.to_dict()
    workflow_dict["events"] = [e.to_dict() for e in workflow.events]
    
    return {
        "workflow": workflow_dict
    }

@router.post("/{workflow_id}/send")
async def send_workflow(
    workflow_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Send workflow to customer (if not already sent)"""
    
    workflow = db.query(DocumentWorkflow).filter(
        DocumentWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Check permissions
    if current_user.role == "user" and workflow.initiated_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already sent
    if workflow.status != WorkflowStatus.INITIATED:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow already in status: {workflow.status}"
        )
    
    # Send to DocuSeal
    form_data = {**workflow.template.default_values, **workflow.form_data}
    
    result = await docuseal_service.create_submission(
        db=db,
        workflow=workflow,
        customer_email=workflow.customer.email,
        customer_name=workflow.customer.contact_name,
        form_data=form_data
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send document: {result['error']}"
        )
    
    return {
        "success": True,
        "workflow": workflow.to_dict(),
        "signing_url": result.get("signing_url")
    }

@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Cancel workflow"""
    
    workflow = db.query(DocumentWorkflow).filter(
        DocumentWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Check permissions
    if current_user.role == "user" and workflow.initiated_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if can be cancelled
    if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel workflow in status: {workflow.status}"
        )
    
    # Update status
    workflow.status = WorkflowStatus.CANCELLED
    workflow.notes = f"{workflow.notes}\nCancelled: {reason}" if reason else workflow.notes
    
    # Log event
    event = WorkflowEvent(
        workflow_id=workflow.id,
        event_type="workflow_cancelled",
        event_description=f"Workflow cancelled by {current_user.get_full_name()}",
        event_data={"reason": reason} if reason else {},
        user_id=current_user.id,
        user_email=current_user.email
    )
    
    db.add(event)
    db.commit()
    
    return {
        "success": True,
        "workflow": workflow.to_dict()
    }

@router.post("/webhook")
async def handle_docuseal_webhook(
    webhook_data: Dict[str, Any],
    db: Session = Depends(get_db_session)
):
    """Handle DocuSeal webhook events"""
    
    submission_id = webhook_data.get("submission_id")
    if not submission_id:
        return {"status": "ignored", "reason": "No submission_id"}
    
    # Find workflow by submission ID
    workflow = db.query(DocumentWorkflow).filter(
        DocumentWorkflow.docuseal_submission_id == str(submission_id)
    ).first()
    
    if not workflow:
        return {"status": "ignored", "reason": "Workflow not found"}
    
    # Update workflow from webhook
    success = await docuseal_service.update_workflow_from_webhook(
        db=db,
        workflow=workflow,
        webhook_data=webhook_data
    )
    
    return {
        "status": "processed" if success else "error",
        "workflow_id": workflow.id
    }