"""
Email Service
Clean email integration for notifications
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending notifications"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            
            return {"status": "healthy", "smtp_host": self.smtp_host}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def send_document_initiation_email(
        self,
        recipient_email: str,
        customer_name: str,
        document_type: str,
        signing_url: str,
        sales_person_name: str = "Better Day Energy Sales Team"
    ) -> Dict[str, Any]:
        """Send document initiation email to customer"""
        
        try:
            subject = f"Document Signature Required - {document_type}"
            
            # Create HTML email content
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #1f4e79, #2563eb); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                        <h1 style="margin: 0; font-size: 24px;">Better Day Energy</h1>
                        <p style="margin: 10px 0 0 0; font-size: 16px;">Document Signature Required</p>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px;">
                        <p>Dear {customer_name},</p>
                        
                        <p>You have been sent a <strong>{document_type}</strong> document that requires your electronic signature.</p>
                        
                        <p>This document has been prepared by {sales_person_name} and is ready for your review and signature.</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{signing_url}" 
                               style="background: #2563eb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                                📝 Review and Sign Document
                            </a>
                        </div>
                        
                        <div style="background: #e3f2fd; padding: 20px; border-radius: 6px; margin: 20px 0;">
                            <h3 style="margin: 0 0 10px 0; color: #1f4e79;">Important Information</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li>This document is legally binding once signed</li>
                                <li>You can complete the signing process on any device</li>
                                <li>The document will be securely stored after completion</li>
                                <li>You will receive a copy via email once signed</li>
                            </ul>
                        </div>
                        
                        <p>If you have any questions about this document, please contact our sales team at:</p>
                        <ul>
                            <li><strong>Email:</strong> {self.from_email}</li>
                            <li><strong>Phone:</strong> (Contact your sales representative)</li>
                        </ul>
                        
                        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                        
                        <p style="font-size: 12px; color: #6c757d; text-align: center;">
                            This email was sent by Better Day Energy's document signing system.<br>
                            The document link is secure and expires after use.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create text version
            text_body = f"""
            Dear {customer_name},

            You have been sent a {document_type} document that requires your electronic signature.

            This document has been prepared by {sales_person_name} and is ready for your review and signature.

            Please click the following link to review and sign the document:
            {signing_url}

            Important Information:
            - This document is legally binding once signed
            - You can complete the signing process on any device
            - The document will be securely stored after completion
            - You will receive a copy via email once signed

            If you have any questions about this document, please contact our sales team at {self.from_email}.

            Best regards,
            Better Day Energy Team
            """
            
            return self._send_email(
                recipient_email,
                subject,
                text_body,
                html_body
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to send initiation email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_completion_notification(
        self,
        recipient_email: str,
        customer_name: str,
        document_type: str,
        document_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send completion notification to sales team"""
        
        try:
            subject = f"Document Completed - {document_type} - {customer_name}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                        <h1 style="margin: 0; font-size: 20px;">✅ Document Completed</h1>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px;">
                        <p><strong>{customer_name}</strong> has successfully completed and signed the <strong>{document_type}</strong> document.</p>
                        
                        <div style="background: #d1edcc; padding: 20px; border-radius: 6px; margin: 20px 0;">
                            <h3 style="margin: 0 0 10px 0; color: #2e7d32;">Document Details</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>Customer:</strong> {customer_name}</li>
                                <li><strong>Document Type:</strong> {document_type}</li>
                                <li><strong>Completed:</strong> {datetime.now().strftime('%Y-%m-%d at %I:%M %p')}</li>
                                <li><strong>Status:</strong> Signed and Completed</li>
                            </ul>
                        </div>
                        
                        {f'<p><strong>Download Document:</strong> <a href="{document_url}">Download PDF</a></p>' if document_url else ''}
                        
                        <p>The signed document has been securely stored and is available in your dashboard.</p>
                        
                        <p>Next steps:</p>
                        <ul>
                            <li>Review the completed document</li>
                            <li>Proceed with next steps in the sales process</li>
                            <li>Contact the customer if needed</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Document Completed - {document_type}

            {customer_name} has successfully completed and signed the {document_type} document.

            Document Details:
            - Customer: {customer_name}
            - Document Type: {document_type}
            - Completed: {datetime.now().strftime('%Y-%m-%d at %I:%M %p')}
            - Status: Signed and Completed

            {f'Download Document: {document_url}' if document_url else ''}

            The signed document has been securely stored and is available in your dashboard.

            Next steps:
            - Review the completed document
            - Proceed with next steps in the sales process
            - Contact the customer if needed

            Best regards,
            Better Day Energy Document System
            """
            
            return self._send_email(
                recipient_email,
                subject,
                text_body,
                html_body
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to send completion notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str
    ) -> Dict[str, Any]:
        """Send email with both text and HTML content"""
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Better Day Energy <{self.from_email}>"
            msg['To'] = recipient_email
            
            # Attach parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {recipient_email}: {subject}")
            return {"success": True, "recipient": recipient_email, "subject": subject}
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {recipient_email}: {str(e)}")
            return {"success": False, "error": str(e)}