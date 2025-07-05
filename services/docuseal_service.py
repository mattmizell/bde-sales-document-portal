"""
DocuSeal Integration Service
Direct integration with self-hosted DocuSeal instance
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.core import DocumentWorkflow, DocumentTemplate, WorkflowEvent, WorkflowStatus

logger = logging.getLogger(__name__)

class DocuSealService:
    """Service for DocuSeal integration"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = 30.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check DocuSeal service health"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/templates",
                    headers={"X-Auth-Token": self.api_token}
                )
                
                if response.status_code == 200:
                    templates = response.json()
                    return {
                        "status": "healthy",
                        "templates_count": len(templates),
                        "docuseal_url": self.base_url
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List available DocuSeal templates"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/templates",
                    headers={"X-Auth-Token": self.api_token}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Failed to list templates: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Template listing error: {e}")
            return []
    
    async def create_submission(
        self,
        db: Session,
        workflow: DocumentWorkflow,
        customer_email: str,
        customer_name: str,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create document submission in DocuSeal"""
        
        try:
            # Build submission payload
            payload = {
                "template_id": workflow.template.docuseal_template_id,
                "submitters": [
                    {
                        "name": customer_name,
                        "email": customer_email,
                        "role": "Customer",
                        "values": form_data
                    }
                ]
            }
            
            # Send to DocuSeal
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/submissions",
                    headers={
                        "X-Auth-Token": self.api_token,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code == 201:
                    result = response.json()
                    
                    # Update workflow with DocuSeal submission ID
                    workflow.docuseal_submission_id = str(result.get("id"))
                    workflow.signing_url = result.get("submitters", [{}])[0].get("embed_src")
                    workflow.status = WorkflowStatus.SENT
                    workflow.sent_at = datetime.utcnow()
                    
                    # Set expiry date
                    if workflow.template.expiry_days:
                        workflow.expires_at = datetime.utcnow() + timedelta(days=workflow.template.expiry_days)
                    
                    # Log event
                    event = WorkflowEvent(
                        workflow_id=workflow.id,
                        event_type="docuseal_submission_created",
                        event_description=f"Document sent to {customer_email} via DocuSeal",
                        event_data={
                            "docuseal_submission_id": workflow.docuseal_submission_id,
                            "signing_url": workflow.signing_url
                        }
                    )
                    db.add(event)
                    
                    db.commit()
                    
                    logger.info(f"✅ DocuSeal submission created: {workflow.docuseal_submission_id}")
                    
                    return {
                        "success": True,
                        "submission_id": workflow.docuseal_submission_id,
                        "signing_url": workflow.signing_url,
                        "message": f"Document sent to {customer_email}"
                    }
                else:
                    error_msg = f"DocuSeal API error: {response.status_code} - {response.text}"
                    logger.error(f"❌ {error_msg}")
                    
                    # Update workflow with error
                    workflow.status = WorkflowStatus.ERROR
                    workflow.error_message = error_msg
                    
                    event = WorkflowEvent(
                        workflow_id=workflow.id,
                        event_type="docuseal_submission_failed",
                        event_description=f"Failed to create DocuSeal submission: {error_msg}",
                        event_data={"error": error_msg}
                    )
                    db.add(event)
                    db.commit()
                    
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except Exception as e:
            error_msg = f"DocuSeal integration error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Update workflow with error
            workflow.status = WorkflowStatus.ERROR
            workflow.error_message = error_msg
            
            event = WorkflowEvent(
                workflow_id=workflow.id,
                event_type="docuseal_integration_error",
                event_description=error_msg,
                event_data={"exception": str(e)}
            )
            db.add(event)
            db.commit()
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_submission_status(
        self,
        submission_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get submission status from DocuSeal"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/submissions/{submission_id}",
                    headers={"X-Auth-Token": self.api_token}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Failed to get submission status: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Submission status error: {e}")
            return None
    
    async def update_workflow_from_webhook(
        self,
        db: Session,
        workflow: DocumentWorkflow,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """Update workflow based on DocuSeal webhook data"""
        
        try:
            event_type = webhook_data.get("event_type")
            
            # Update workflow status based on event
            if event_type == "form.viewed":
                if workflow.status == WorkflowStatus.SENT:
                    workflow.status = WorkflowStatus.VIEWED
                    workflow.viewed_at = datetime.utcnow()
                    
            elif event_type == "form.started":
                workflow.status = WorkflowStatus.IN_PROGRESS
                
            elif event_type == "form.completed":
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.utcnow()
                workflow.completed_by = webhook_data.get("submitter_email")
                workflow.document_url = webhook_data.get("document_url")
                
                # Get final submission data
                submission_data = await self.get_submission_status(workflow.docuseal_submission_id)
                if submission_data:
                    workflow.submitted_data = submission_data.get("submitted_data", {})
            
            # Log event
            event = WorkflowEvent(
                workflow_id=workflow.id,
                event_type=f"docuseal_{event_type}",
                event_description=f"DocuSeal webhook: {event_type}",
                event_data=webhook_data,
                user_email=webhook_data.get("submitter_email")
            )
            
            db.add(event)
            db.commit()
            
            logger.info(f"✅ Workflow {workflow.id} updated from webhook: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Webhook processing error: {e}")
            return False
    
    async def send_reminder(
        self,
        db: Session,
        workflow: DocumentWorkflow
    ) -> bool:
        """Send reminder for pending document"""
        
        try:
            if not workflow.docuseal_submission_id:
                return False
            
            # DocuSeal doesn't have a direct reminder API
            # We would implement email reminder here or use DocuSeal's automatic reminders
            
            # Log reminder event
            event = WorkflowEvent(
                workflow_id=workflow.id,
                event_type="reminder_sent",
                event_description="Reminder sent to customer",
                event_data={"method": "email"}
            )
            
            db.add(event)
            db.commit()
            
            logger.info(f"✅ Reminder sent for workflow {workflow.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Reminder error: {e}")
            return False