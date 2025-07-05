"""
CRM API Routes
Clean integration with Less Annoying CRM via cache bridge
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
import logging

from services.crm_bridge import (
    CRMBridge,
    ContactSearchRequest,
    ContactCreateRequest,
    ContactUpdateRequest,
    search_contacts,
    get_contact_by_id,
    create_contact,
    get_crm_health
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/crm", tags=["CRM Integration"])

# Initialize CRM bridge
crm_bridge = CRMBridge()

@router.get("/health")
async def crm_health_check():
    """Check CRM bridge health and cache status"""
    
    try:
        health_data = await get_crm_health()
        
        # Determine overall health
        cache_hit_rate = health_data.get("cache_hit_rate", 0)
        total_contacts = health_data.get("total_contacts", 0)
        
        if total_contacts == 0:
            status = "empty"
        elif cache_hit_rate > 80:
            status = "healthy"
        elif cache_hit_rate > 50:
            status = "degraded"
        else:
            status = "needs_refresh"
        
        return {
            "status": status,
            "cache_stats": health_data,
            "recommendations": _get_health_recommendations(health_data)
        }
        
    except Exception as e:
        logger.error(f"❌ CRM health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "cache_stats": {},
            "recommendations": ["Check CRM service connectivity"]
        }

@router.post("/contacts/search")
async def search_crm_contacts(search_request: ContactSearchRequest):
    """Search contacts in CRM cache"""
    
    try:
        contacts = await search_contacts(search_request)
        
        return {
            "contacts": contacts,
            "count": len(contacts),
            "query": search_request.query,
            "company_filter": search_request.company_filter,
            "limit": search_request.limit
        }
        
    except Exception as e:
        logger.error(f"❌ Contact search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contact search failed: {e}")

@router.get("/contacts/{contact_id}")
async def get_crm_contact(contact_id: str):
    """Get single contact by ID from cache"""
    
    try:
        contact = await get_contact_by_id(contact_id)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {
            "contact": contact,
            "cache_status": contact.get("cache_status", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Contact lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contact lookup failed: {e}")

@router.post("/contacts")
async def create_crm_contact(
    contact_data: ContactCreateRequest,
    background_tasks: BackgroundTasks
):
    """Create new contact in CRM"""
    
    try:
        result = await create_contact(contact_data)
        
        # Schedule cache refresh in background
        background_tasks.add_task(_refresh_cache_background)
        
        logger.info(f"✅ Contact created: {result.get('contact_id')}")
        
        return {
            "success": True,
            "contact": result,
            "message": "Contact created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Contact creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contact creation failed: {e}")

@router.post("/sync")
async def sync_crm_cache(background_tasks: BackgroundTasks):
    """Trigger full CRM cache sync"""
    
    try:
        # Start sync in background
        background_tasks.add_task(_full_sync_background)
        
        return {
            "success": True,
            "message": "CRM sync started in background",
            "estimated_duration": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"❌ CRM sync initiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync initiation failed: {e}")

@router.get("/stats")
async def get_crm_stats():
    """Get detailed CRM cache statistics"""
    
    try:
        stats = await get_crm_health()
        
        # Add additional stats
        cache_age_hours = None
        if stats.get("last_sync"):
            from datetime import datetime
            last_sync = datetime.fromisoformat(stats["last_sync"].replace('Z', '+00:00'))
            cache_age_hours = (datetime.utcnow() - last_sync.replace(tzinfo=None)).total_seconds() / 3600
        
        return {
            "cache_stats": stats,
            "cache_age_hours": round(cache_age_hours, 1) if cache_age_hours else None,
            "performance": {
                "cache_hit_rate": stats.get("cache_hit_rate", 0),
                "response_time": "< 100ms (cached)",
                "availability": "99.9%"
            },
            "recommendations": _get_optimization_recommendations(stats)
        }
        
    except Exception as e:
        logger.error(f"❌ CRM stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {e}")

@router.get("/contacts")
async def list_crm_contacts(
    limit: int = 50,
    search: Optional[str] = None,
    company: Optional[str] = None
):
    """List contacts with optional filtering"""
    
    try:
        search_request = ContactSearchRequest(
            query=search,
            company_filter=company,
            limit=min(limit, 200)  # Cap at 200 for performance
        )
        
        contacts = await search_contacts(search_request)
        
        return {
            "contacts": contacts,
            "count": len(contacts),
            "limit": limit,
            "filters": {
                "search": search,
                "company": company
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Contact listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contact listing failed: {e}")

# Background task functions
async def _refresh_cache_background():
    """Background task to refresh CRM cache"""
    try:
        result = await crm_bridge.sync_contacts_from_lacrm(limit=100)
        logger.info(f"✅ Background cache refresh completed: {result}")
    except Exception as e:
        logger.error(f"❌ Background cache refresh failed: {e}")

async def _full_sync_background():
    """Background task for full CRM sync"""
    try:
        result = await crm_bridge.sync_contacts_from_lacrm(limit=2000)
        logger.info(f"✅ Full CRM sync completed: {result}")
    except Exception as e:
        logger.error(f"❌ Full CRM sync failed: {e}")

# Helper functions
def _get_health_recommendations(health_data: Dict[str, Any]) -> List[str]:
    """Get health recommendations based on cache stats"""
    
    recommendations = []
    cache_hit_rate = health_data.get("cache_hit_rate", 0)
    total_contacts = health_data.get("total_contacts", 0)
    
    if total_contacts == 0:
        recommendations.append("Initialize CRM cache with first sync")
    elif cache_hit_rate < 50:
        recommendations.append("Run full CRM sync to refresh stale data")
    elif cache_hit_rate < 80:
        recommendations.append("Consider increasing sync frequency")
    
    if health_data.get("last_sync") is None:
        recommendations.append("No sync history found - run initial sync")
    
    return recommendations or ["CRM cache is healthy"]

def _get_optimization_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Get optimization recommendations"""
    
    recommendations = []
    cache_hit_rate = stats.get("cache_hit_rate", 0)
    
    if cache_hit_rate > 95:
        recommendations.append("Excellent cache performance")
    elif cache_hit_rate > 80:
        recommendations.append("Good cache performance - consider hourly sync")
    else:
        recommendations.append("Increase sync frequency for better performance")
    
    return recommendations