"""
Database Models for BDE Sales Document Portal
Clean, optimized models for DocuSeal integration
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .connection import Base

class Customer(Base):
    """Customer information"""
    __tablename__ = 'customers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50))
    
    # Address
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    
    # Metadata
    customer_type = Column(String(50), default='prospect')  # prospect, active, inactive
    is_vip = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflows = relationship("DocumentWorkflow", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, company={self.company_name})>"

class DocumentWorkflow(Base):
    """Document workflow tracking"""
    __tablename__ = 'document_workflows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    
    # Workflow identification
    workflow_type = Column(String(50), nullable=False)  # p66_loi, vp_racing_loi, eft_form, customer_setup
    workflow_name = Column(String(255), nullable=False)
    
    # DocuSeal integration
    docuseal_template_id = Column(String(255))
    docuseal_submission_id = Column(String(255))
    docuseal_document_id = Column(String(255))
    
    # Status tracking
    status = Column(String(50), default='draft')  # draft, initiated, viewed, in_progress, completed, cancelled
    
    # Data storage
    form_data = Column(JSON, default=dict)
    pre_filled_data = Column(JSON, default=dict)
    customer_data = Column(JSON, default=dict)
    
    # Workflow participants
    initiated_by = Column(String(255))  # Sales person email
    initiated_at = Column(DateTime)
    completed_by = Column(String(255))  # Customer email
    completed_at = Column(DateTime)
    
    # Document URLs
    document_url = Column(String(500))  # Final signed document
    pdf_url = Column(String(500))  # PDF download URL
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="workflows")
    events = relationship("WorkflowEvent", back_populates="workflow")
    emails = relationship("EmailLog", back_populates="workflow")
    
    def __repr__(self):
        return f"<DocumentWorkflow(id={self.id}, type={self.workflow_type}, status={self.status})>"

class WorkflowEvent(Base):
    """Audit trail for workflow events"""
    __tablename__ = 'workflow_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('document_workflows.id'), nullable=False)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # created, initiated, viewed, signed, completed
    event_description = Column(Text)
    event_data = Column(JSON, default=dict)
    
    # Context
    user_email = Column(String(255))
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(Text)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("DocumentWorkflow", back_populates="events")
    
    def __repr__(self):
        return f"<WorkflowEvent(id={self.id}, type={self.event_type})>"

class EmailLog(Base):
    """Email communication log"""
    __tablename__ = 'email_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('document_workflows.id'))
    
    # Email details
    email_type = Column(String(100), nullable=False)  # initiation, reminder, completion
    recipient_email = Column(String(255), nullable=False)
    sender_email = Column(String(255), default='transaction.coordinator.agent@gmail.com')
    subject = Column(String(500))
    
    # Status
    status = Column(String(50), default='sent')  # sent, delivered, failed, bounced
    
    # External references
    message_id = Column(String(255))  # SMTP message ID
    
    # Timestamp
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("DocumentWorkflow", back_populates="emails")
    
    def __repr__(self):
        return f"<EmailLog(id={self.id}, type={self.email_type}, recipient={self.recipient_email})>"

class DocumentTemplate(Base):
    """DocuSeal template management"""
    __tablename__ = 'document_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template identification
    template_name = Column(String(255), nullable=False)
    template_type = Column(String(100), nullable=False)  # p66_loi, vp_racing_loi, eft_form
    version = Column(String(50), default='1.0')
    
    # DocuSeal integration
    docuseal_template_id = Column(String(255))
    
    # Template configuration
    field_mappings = Column(JSON, default=dict)
    default_values = Column(JSON, default=dict)
    
    # Metadata
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Usage tracking
    usage_count = Column(String, default='0')
    last_used_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    
    def __repr__(self):
        return f"<DocumentTemplate(id={self.id}, name={self.template_name})>"

# CRM Bridge Models
class CRMContactsCache(Base):
    """CRM contacts cache for fast lookups"""
    __tablename__ = 'crm_contacts_cache'
    
    contact_id = Column(String(255), primary_key=True)
    
    # Name fields
    name = Column(String(500))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Contact information
    company_name = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(JSON)  # JSONB for address data
    
    # Cache metadata
    sync_status = Column(String(50), default='synced')  # synced, pending_sync, failed
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CRMContact(id={self.contact_id}, name={self.name})>"

class CRMWriteQueue(Base):
    """Queue for CRM write operations"""
    __tablename__ = 'crm_write_queue'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Operation details
    operation = Column(String(100), nullable=False)  # create_contact, update_contact
    data = Column(JSON, nullable=False)
    
    # Status tracking
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<CRMWriteQueue(id={self.id}, operation={self.operation}, status={self.status})>"

class CRMBridgeAuditLog(Base):
    """Audit log for CRM bridge operations"""
    __tablename__ = 'crm_bridge_audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Operation details
    app_name = Column(String(100))
    operation = Column(String(100), nullable=False)
    details = Column(JSON)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CRMAuditLog(id={self.id}, app={self.app_name}, operation={self.operation})>"