"""
DocuSeal Integration Service
Handles communication with external DocuSeal microservice
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class DocuSealIntegration:
    """Integration with external DocuSeal service"""
    
    def __init__(self, service_url: str):
        self.service_url = service_url.rstrip('/')
        self.timeout = 30.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check external DocuSeal service health"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "service_url": self.service_url,
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            return {
                "status": "error",
                "error": "Service timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def initiate_document(
        self,
        template_id: str,
        customer_email: str,
        customer_name: str,
        form_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initiate document signing via external service"""
        
        try:
            payload = {
                "template_id": template_id,
                "customer_email": customer_email,
                "customer_name": customer_name,
                "form_data": form_data or {}
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/api/v1/documents/initiate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "submission_id": result.get("submission_id"),
                        "signing_url": result.get("signing_url"),
                        "message": result.get("message")
                    }
                else:
                    logger.error(f"❌ DocuSeal service error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Service error: {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            logger.error("❌ DocuSeal service timeout")
            return {
                "success": False,
                "error": "Service timeout"
            }
        except Exception as e:
            logger.error(f"❌ DocuSeal integration error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_document_status(self, submission_id: str) -> Dict[str, Any]:
        """Get document status from external service"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/documents/{submission_id}/status"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"DocuSeal service error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="DocuSeal service timeout")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DocuSeal integration error: {str(e)}")
    
    async def download_document(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Download document from external service"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/documents/{submission_id}/download"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    logger.error(f"❌ Document download error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Document download error: {e}")
            return None
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List available templates from external service"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/api/v1/templates")
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("templates", [])
                else:
                    logger.error(f"❌ Template listing error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Template listing error: {e}")
            return []
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template details from external service"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.service_url}/api/v1/templates/{template_id}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("template")
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Template lookup error: {e}")
            return None