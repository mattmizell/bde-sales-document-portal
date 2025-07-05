"""
Core Models for Integrated Sales Portal
Extensible system for managing customers and document workflows
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
# Import Base from auth module to ensure consistency
from models.auth import Base

class WorkflowStatus(str, Enum):
    """Document workflow status enumeration"""
    DRAFT = "draft"
    INITIATED = "initiated"
    SENT = "sent"
    VIEWED = "viewed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    ERROR = "error"

class DocumentType(str, Enum):
    """Document type enumeration"""
    CUSTOMER_SETUP = "customer_setup"
    EFT_AGREEMENT = "eft_agreement"
    VP_RACING_LOI = "vp_racing_loi"
    P66_LOI = "p66_loi"
    CUSTOM = "custom"

class Customer(Base):
    """Customer information management"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    
    # Address information
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), default="USA")
    
    # Business information
    tax_id = Column(String(50), nullable=True)
    business_type = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    
    # CRM integration
    crm_contact_id = Column(String(100), nullable=True, index=True)
    crm_last_sync = Column(DateTime, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, nullable=True)  # User ID
    
    # Relationships
    workflows = relationship("DocumentWorkflow", back_populates="customer", cascade="all, delete-orphan")
    
    def get_full_address(self) -> str:
        """Get formatted full address"""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ", ".join([p for p in parts if p])
    
    def to_dict(self) -> dict:
        """Convert customer to dictionary"""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.get_full_address(),
            "tax_id": self.tax_id,
            "business_type": self.business_type,
            "website": self.website,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "crm_contact_id": self.crm_contact_id,
            "workflow_count": len(self.workflows) if self.workflows else 0
        }

class DocumentTemplate(Base):
    """Document template configuration"""
    __tablename__ = "document_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # DocumentType enum
    description = Column(Text, nullable=True)
    
    # DocuSeal integration
    docuseal_template_id = Column(Integer, nullable=False, index=True)
    
    # Template configuration
    required_fields = Column(JSON, default=list)  # List of required field names
    field_mappings = Column(JSON, default=dict)   # Field name mappings
    default_values = Column(JSON, default=dict)   # Default field values
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    auto_send = Column(Boolean, default=True, nullable=False)  # Auto-send to customer
    expiry_days = Column(Integer, default=30)  # Days before document expires
    reminder_days = Column(Integer, default=7)  # Days between reminders
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, nullable=True)
    
    # Relationships
    workflows = relationship("DocumentWorkflow", back_populates="template")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "document_type": self.document_type,
            "description": self.description,
            "docuseal_template_id": self.docuseal_template_id,
            "required_fields": self.required_fields,
            "field_mappings": self.field_mappings,
            "default_values": self.default_values,
            "is_active": self.is_active,
            "auto_send": self.auto_send,
            "expiry_days": self.expiry_days,
            "reminder_days": self.reminder_days,
            "created_at": self.created_at.isoformat(),
            "workflow_count": len(self.workflows) if self.workflows else 0
        }

class DocumentWorkflow(Base):
    """Document workflow tracking"""
    __tablename__ = "document_workflows"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=False, index=True)
    initiated_by_id = Column(Integer, nullable=False, index=True)  # User ID
    
    # Workflow identification
    workflow_name = Column(String(255), nullable=False)
    workflow_type = Column(String(50), nullable=False, index=True)  # DocumentType enum
    
    # DocuSeal integration
    docuseal_submission_id = Column(String(100), nullable=True, unique=True, index=True)
    docuseal_template_id = Column(Integer, nullable=True)
    
    # Status tracking
    status = Column(String(50), default=WorkflowStatus.DRAFT, nullable=False, index=True)
    
    # Form data and results
    form_data = Column(JSON, default=dict)  # Original form data
    submitted_data = Column(JSON, default=dict)  # Data from completed form
    
    # Timing
    initiated_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Results
    document_url = Column(String(500), nullable=True)  # Final signed document URL
    signing_url = Column(String(500), nullable=True)   # Customer signing URL
    completed_by = Column(String(255), nullable=True)  # Customer email who completed
    
    # Metadata
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="workflows")
    template = relationship("DocumentTemplate", back_populates="workflows")
    events = relationship("WorkflowEvent", back_populates="workflow", cascade="all, delete-orphan")
    
    def is_active(self) -> bool:
        """Check if workflow is in active state"""
        return self.status in [
            WorkflowStatus.INITIATED, 
            WorkflowStatus.SENT, 
            WorkflowStatus.VIEWED, 
            WorkflowStatus.IN_PROGRESS
        ]
    
    def is_completed(self) -> bool:
        """Check if workflow is completed"""
        return self.status == WorkflowStatus.COMPLETED
    
    def days_since_initiated(self) -> int:
        """Get days since workflow was initiated"""
        if not self.initiated_at:
            return 0
        return (datetime.utcnow() - self.initiated_at).days
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "template_id": self.template_id,
            "initiated_by_id": self.initiated_by_id,
            "workflow_name": self.workflow_name,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "docuseal_submission_id": self.docuseal_submission_id,
            "form_data": self.form_data,
            "submitted_data": self.submitted_data,
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "document_url": self.document_url,
            "signing_url": self.signing_url,
            "completed_by": self.completed_by,
            "notes": self.notes,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active(),
            "is_completed": self.is_completed(),
            "days_since_initiated": self.days_since_initiated()
        }

class WorkflowEvent(Base):
    """Workflow event tracking for audit trail"""
    __tablename__ = "workflow_events"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("document_workflows.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    event_data = Column(JSON, default=dict)
    
    # User context
    user_email = Column(String(255), nullable=True)
    user_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    workflow = relationship("DocumentWorkflow", back_populates="events")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "event_type": self.event_type,
            "event_description": self.event_description,
            "event_data": self.event_data,
            "user_email": self.user_email,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat()
        }