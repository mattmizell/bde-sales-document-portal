"""
Core Models for Integrated Sales Portal
Extensible system for managing customers and document workflows
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
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
    
    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    contact_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="USA")
    
    # Business information
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # CRM integration
    crm_contact_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    crm_last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status and metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # User ID
    
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
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    document_type: Mapped[str] = mapped_column(String(50), index=True)  # DocumentType enum
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # DocuSeal integration
    docuseal_template_id: Mapped[int] = mapped_column(index=True)
    
    # Template configuration
    required_fields: Mapped[List[str]] = mapped_column(JSON, default=list)  # List of required field names
    field_mappings: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)   # Field name mappings
    default_values: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)   # Default field values
    
    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_send: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-send to customer
    expiry_days: Mapped[int] = mapped_column(default=30)  # Days before document expires
    reminder_days: Mapped[int] = mapped_column(default=7)  # Days between reminders
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    
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
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relationships
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id"), index=True)
    initiated_by_id: Mapped[int] = mapped_column(index=True)  # User ID
    
    # Workflow identification
    workflow_name: Mapped[str] = mapped_column(String(255))
    workflow_type: Mapped[str] = mapped_column(String(50), index=True)  # DocumentType enum
    
    # DocuSeal integration
    docuseal_submission_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    docuseal_template_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default=WorkflowStatus.DRAFT, index=True)
    
    # Form data and results
    form_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Original form data
    submitted_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Data from completed form
    
    # Timing
    initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Results
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Final signed document URL
    signing_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)   # Customer signing URL
    completed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Customer email who completed
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("document_workflows.id"), index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    event_description: Mapped[str] = mapped_column(Text)
    event_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # User context
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
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