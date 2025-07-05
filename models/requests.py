"""
Request Models
Pydantic models for API requests
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class CustomerCreateRequest(BaseModel):
    """Request model for creating customers"""
    company_name: str
    contact_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    customer_type: str = "prospect"

class DocumentInitiateRequest(BaseModel):
    """Request model for initiating document signing"""
    customer_id: str
    customer_email: EmailStr
    customer_name: str
    document_type: str  # p66_loi, vp_racing_loi, eft_form, customer_setup
    template_id: str  # DocuSeal template ID
    form_data: Dict[str, Any] = {}
    initiated_by: EmailStr

class WebhookEventRequest(BaseModel):
    """Request model for DocuSeal webhook events"""
    event_type: str  # form.completed, form.viewed, form.started
    submission_id: str
    submitter_email: Optional[EmailStr] = None
    document_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    additional_data: Dict[str, Any] = {}

class TemplateCreateRequest(BaseModel):
    """Request model for creating document templates"""
    template_name: str
    template_type: str  # p66_loi, vp_racing_loi, eft_form, customer_setup
    html_content: str
    description: Optional[str] = None
    field_mappings: Dict[str, Any] = {}
    default_values: Dict[str, Any] = {}

class WorkflowStatusRequest(BaseModel):
    """Request model for workflow status updates"""
    workflow_id: str
    status: str
    notes: Optional[str] = None
    updated_by: EmailStr