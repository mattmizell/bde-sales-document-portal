"""
Customer Management API Routes
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr

from database.connection import get_db_session
from services.auth_service import get_current_user
from models.auth import User
from models.core import Customer

router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])

# Request/Response models
class CustomerCreateRequest(BaseModel):
    company_name: str
    contact_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None

class CustomerUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

@router.post("/")
async def create_customer(
    customer_data: CustomerCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new customer"""
    
    # Check if customer already exists
    existing = db.query(Customer).filter(
        Customer.email == customer_data.email
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Customer with this email already exists"
        )
    
    # Create customer
    customer = Customer(
        **customer_data.dict(),
        created_by_id=current_user.id
    )
    
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return {
        "success": True,
        "customer": customer.to_dict()
    }

@router.get("/")
async def list_customers(
    search: Optional[str] = Query(None, description="Search by company name, contact name, or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """List customers with optional search and filters"""
    
    query = db.query(Customer)
    
    # Search filter
    if search:
        search_filter = or_(
            Customer.company_name.ilike(f"%{search}%"),
            Customer.contact_name.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Active filter
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    customers = query.offset(skip).limit(limit).all()
    
    return {
        "customers": [customer.to_dict() for customer in customers],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{customer_id}")
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get customer by ID"""
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer": customer.to_dict()
    }

@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    update_data: CustomerUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update customer information"""
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    
    return {
        "success": True,
        "customer": customer.to_dict()
    }

@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete customer (soft delete)"""
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if customer has active workflows
    active_workflows = [w for w in customer.workflows if w.is_active()]
    if active_workflows:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete customer with {len(active_workflows)} active workflows"
        )
    
    # Soft delete
    customer.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "Customer deactivated successfully"
    }

@router.get("/{customer_id}/workflows")
async def get_customer_workflows(
    customer_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get all workflows for a customer"""
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    workflows = sorted(customer.workflows, key=lambda w: w.created_at, reverse=True)
    
    return {
        "customer": customer.to_dict(),
        "workflows": [w.to_dict() for w in workflows],
        "total": len(workflows),
        "active": len([w for w in workflows if w.is_active()]),
        "completed": len([w for w in workflows if w.is_completed()])
    }

@router.post("/import-from-crm")
async def import_from_crm(
    crm_contact_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Import customer from CRM"""
    
    # TODO: Integrate with CRM bridge service
    # For now, return placeholder
    
    return {
        "success": False,
        "message": "CRM import not yet implemented"
    }