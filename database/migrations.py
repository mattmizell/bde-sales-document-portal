"""
Database Migrations for BDE Sales Document Portal
Creates all required tables for clean v2 architecture
"""

from sqlalchemy import text
from database.connection import engine
import logging

logger = logging.getLogger(__name__)

def create_crm_cache_tables():
    """Create CRM bridge cache tables"""
    
    crm_cache_sql = """
    -- CRM Contacts Cache Table
    CREATE TABLE IF NOT EXISTS crm_contacts_cache (
        contact_id VARCHAR(100) PRIMARY KEY,
        name VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        company_name VARCHAR(255),
        email VARCHAR(255),
        phone VARCHAR(100),
        address JSONB DEFAULT '{}',
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        last_sync TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    );

    -- Indexes for fast searching
    CREATE INDEX IF NOT EXISTS idx_crm_contacts_name ON crm_contacts_cache(name);
    CREATE INDEX IF NOT EXISTS idx_crm_contacts_company ON crm_contacts_cache(company_name);
    CREATE INDEX IF NOT EXISTS idx_crm_contacts_email ON crm_contacts_cache(email);
    CREATE INDEX IF NOT EXISTS idx_crm_contacts_last_sync ON crm_contacts_cache(last_sync);
    CREATE INDEX IF NOT EXISTS idx_crm_contacts_search ON crm_contacts_cache 
        USING gin(to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(company_name, '') || ' ' || COALESCE(email, '')));

    -- CRM Bridge Audit Log
    CREATE TABLE IF NOT EXISTS crm_bridge_audit_log (
        id SERIAL PRIMARY KEY,
        operation VARCHAR(100) NOT NULL,
        contact_id VARCHAR(100),
        app_name VARCHAR(100),
        details JSONB DEFAULT '{}',
        timestamp TIMESTAMP DEFAULT NOW(),
        success BOOLEAN DEFAULT TRUE,
        error_message TEXT
    );

    -- Index for audit log
    CREATE INDEX IF NOT EXISTS idx_crm_audit_timestamp ON crm_bridge_audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_crm_audit_operation ON crm_bridge_audit_log(operation);
    """
    
    try:
        with engine.connect() as conn:
            # Execute each statement separately
            statements = [stmt.strip() for stmt in crm_cache_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
            
            conn.commit()
            logger.info("✅ CRM cache tables created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create CRM cache tables: {e}")
        raise

def create_all_tables():
    """Create all database tables for the application"""
    
    try:
        # Create main application tables (from models.py)
        from database.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Main application tables created")
        
        # Create CRM cache tables
        create_crm_cache_tables()
        
        # Create any additional tables or indexes
        create_additional_indexes()
        
        logger.info("🎉 All database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Database table creation failed: {e}")
        raise

def create_additional_indexes():
    """Create additional performance indexes"""
    
    additional_indexes_sql = """
    -- Workflow performance indexes
    CREATE INDEX IF NOT EXISTS idx_workflows_customer_status ON document_workflows(customer_id, status);
    CREATE INDEX IF NOT EXISTS idx_workflows_type_status ON document_workflows(workflow_type, status);
    CREATE INDEX IF NOT EXISTS idx_workflows_initiated_date ON document_workflows(initiated_at);
    CREATE INDEX IF NOT EXISTS idx_workflows_completed_date ON document_workflows(completed_at);
    CREATE INDEX IF NOT EXISTS idx_workflows_docuseal_submission ON document_workflows(docuseal_submission_id);

    -- Event tracking indexes
    CREATE INDEX IF NOT EXISTS idx_events_workflow_type ON workflow_events(workflow_id, event_type);
    CREATE INDEX IF NOT EXISTS idx_events_timestamp_desc ON workflow_events(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_events_user_email ON workflow_events(user_email);

    -- Email log indexes
    CREATE INDEX IF NOT EXISTS idx_emails_workflow_type ON email_logs(workflow_id, email_type);
    CREATE INDEX IF NOT EXISTS idx_emails_recipient_sent ON email_logs(recipient_email, sent_at);
    CREATE INDEX IF NOT EXISTS idx_emails_status ON email_logs(status);

    -- Customer search indexes
    CREATE INDEX IF NOT EXISTS idx_customers_company_name ON customers(company_name);
    CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
    CREATE INDEX IF NOT EXISTS idx_customers_created ON customers(created_at);
    
    -- Full-text search for customers
    CREATE INDEX IF NOT EXISTS idx_customers_search ON customers 
        USING gin(to_tsvector('english', company_name || ' ' || contact_name || ' ' || COALESCE(email, '')));
    """
    
    try:
        with engine.connect() as conn:
            statements = [stmt.strip() for stmt in additional_indexes_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
            
            conn.commit()
            logger.info("✅ Additional indexes created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create additional indexes: {e}")
        raise

def create_database_views():
    """Create useful database views for reporting"""
    
    views_sql = """
    -- Workflow summary view
    CREATE OR REPLACE VIEW workflow_summary AS
    SELECT 
        workflow_type,
        status,
        COUNT(*) as count,
        DATE(created_at) as date,
        AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))) as avg_duration_seconds
    FROM document_workflows 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY workflow_type, status, DATE(created_at)
    ORDER BY date DESC, workflow_type, status;

    -- Customer activity view
    CREATE OR REPLACE VIEW customer_activity AS
    SELECT 
        c.id,
        c.company_name,
        c.contact_name,
        c.email,
        COUNT(dw.id) as total_workflows,
        COUNT(CASE WHEN dw.status = 'completed' THEN 1 END) as completed_workflows,
        COUNT(CASE WHEN dw.status IN ('initiated', 'viewed', 'in_progress') THEN 1 END) as active_workflows,
        MAX(dw.created_at) as last_activity,
        AVG(EXTRACT(EPOCH FROM (dw.completed_at - dw.created_at))) as avg_completion_seconds
    FROM customers c
    LEFT JOIN document_workflows dw ON c.id = dw.customer_id
    GROUP BY c.id, c.company_name, c.contact_name, c.email
    ORDER BY last_activity DESC NULLS LAST;

    -- Recent activity view (for dashboard)
    CREATE OR REPLACE VIEW recent_activity AS
    SELECT 
        we.timestamp,
        we.event_type,
        we.event_description,
        c.company_name,
        c.contact_name,
        c.email,
        dw.workflow_type,
        dw.workflow_name,
        dw.status as workflow_status
    FROM workflow_events we
    JOIN document_workflows dw ON we.workflow_id = dw.id
    JOIN customers c ON dw.customer_id = c.id
    WHERE we.timestamp >= CURRENT_DATE - INTERVAL '7 days'
    ORDER BY we.timestamp DESC
    LIMIT 100;

    -- CRM cache health view
    CREATE OR REPLACE VIEW crm_cache_health AS
    SELECT 
        COUNT(*) as total_contacts,
        COUNT(CASE WHEN last_sync > NOW() - INTERVAL '24 hours' THEN 1 END) as fresh_contacts,
        COUNT(CASE WHEN last_sync <= NOW() - INTERVAL '24 hours' OR last_sync IS NULL THEN 1 END) as stale_contacts,
        MAX(last_sync) as last_full_sync,
        ROUND(
            COUNT(CASE WHEN last_sync > NOW() - INTERVAL '24 hours' THEN 1 END)::numeric / 
            COUNT(*)::numeric * 100, 2
        ) as cache_hit_rate
    FROM crm_contacts_cache;
    """
    
    try:
        with engine.connect() as conn:
            statements = [stmt.strip() for stmt in views_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
            
            conn.commit()
            logger.info("✅ Database views created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create database views: {e}")
        raise

def run_all_migrations():
    """Run all database migrations"""
    
    logger.info("🚀 Starting database migrations for BDE Sales Document Portal")
    
    try:
        # Create all tables
        create_all_tables()
        
        # Create views
        create_database_views()
        
        logger.info("🎉 All database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        raise

if __name__ == "__main__":
    run_all_migrations()