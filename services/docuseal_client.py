"""
DocuSeal API Client
Clean integration with DocuSeal external service
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class DocuSealClient:
    """Client for DocuSeal API integration"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'X-Auth-Token': api_token,
            'Content-Type': 'application/json'
        }
        self.timeout = 30.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Test DocuSeal service connectivity"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f'{self.base_url}/api/templates',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    templates = response.json()
                    return {
                        "status": "healthy",
                        "template_count": len(templates),
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    return {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": response.text
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_template_from_html(
        self, 
        name: str, 
        html_content: str, 
        submitters: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Create DocuSeal template from HTML content"""
        try:
            payload = {
                'name': name,
                'html': html_content,
                'submitters': submitters
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/templates/html',
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    template_data = response.json()
                    logger.info(f"✅ Template created: {name} (ID: {template_data.get('id')})")
                    return {
                        "success": True,
                        "template_id": template_data.get('id'),
                        "template_data": template_data
                    }
                else:
                    logger.error(f"❌ Template creation failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            logger.error(f"❌ Template creation exception: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_submission(
        self,
        template_id: str,
        customer_email: str,
        customer_name: str,
        pre_filled_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create submission for document signing"""
        try:
            submitters_data = [{
                "email": customer_email,
                "name": customer_name,
                "values": pre_filled_data or {}
            }]
            
            payload = {
                "template_id": template_id,
                "submitters": submitters_data,
                "send_email": True
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/submissions',
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    submission_data = response.json()
                    
                    # Extract submission ID (handle different response formats)
                    if isinstance(submission_data, list) and len(submission_data) > 0:
                        submission_id = submission_data[0].get('id')
                        signing_url = submission_data[0].get('url')
                    else:
                        submission_id = submission_data.get('id')
                        signing_url = submission_data.get('url')
                    
                    logger.info(f"✅ Submission created: {submission_id} for {customer_email}")
                    return {
                        "success": True,
                        "submission_id": submission_id,
                        "signing_url": signing_url,
                        "submission_data": submission_data
                    }
                else:
                    logger.error(f"❌ Submission creation failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            logger.error(f"❌ Submission creation exception: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_submission_status(self, submission_id: str) -> Dict[str, Any]:
        """Get submission status and details"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/submissions/{submission_id}',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "submission_data": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_templates(self) -> Dict[str, Any]:
        """List available templates"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/templates',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "templates": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_completed_document(self, submission_id: str) -> Dict[str, Any]:
        """Download completed signed document"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/submissions/{submission_id}/download',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "document_data": response.content,
                        "content_type": response.headers.get('content-type', 'application/pdf')
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }