#!/usr/bin/env python3
"""
CRM Bridge Server - Local Test Version
Uses the working CRM bridge with our current database setup
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Set up environment for our database
os.environ['DATABASE_URL'] = 'postgresql://sales_portal_user:flOFZjisR0WKPRnH91ExmmSnvljXPCDR@dpg-d1kjp1h5pdvs73aunge0-a.oregon-postgres.render.com/sales_portal_production'

from database.connection import test_connection, create_tables
from api_routes.crm_routes import router as crm_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BDE CRM Bridge Service",
    description="Local CRM Bridge for testing LACRM integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include CRM routes
app.include_router(crm_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BDE CRM Bridge",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/crm/health",
            "search": "/api/v1/crm/contacts/search",
            "contacts": "/api/v1/crm/contacts",
            "stats": "/api/v1/crm/stats"
        }
    }

@app.get("/health")
async def health_check():
    """Overall health check"""
    
    # Test database connection
    db_health = test_connection()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "database": db_health["status"],
        "message": "CRM Bridge is operational"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    
    logger.info("🚀 BDE CRM Bridge starting up...")
    
    # Test database connection
    db_health = test_connection()
    
    if db_health["status"] == "healthy":
        logger.info("✅ Database connection successful")
        
        # Ensure tables exist
        try:
            create_tables()
            logger.info("✅ Database tables verified")
        except Exception as e:
            logger.warning(f"⚠️ Table verification warning: {e}")
        
        logger.info("🎉 CRM Bridge ready!")
    else:
        logger.error(f"❌ Database connection failed: {db_health['error']}")

if __name__ == "__main__":
    print("🏢 BDE CRM Bridge - Local Test Server")
    print("=" * 40)
    print("🔗 LACRM Integration: Enabled")
    print("🗄️ Database: Render PostgreSQL")
    print("📊 Dashboard: http://localhost:8001")
    print("📖 API Docs: http://localhost:8001/docs")
    print("=" * 40)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )