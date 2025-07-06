#!/usr/bin/env python3
"""
DocuSeal Form Pre-fill Integration for BDE Sales Document Portal
Searches CRM contacts and pre-fills DocuSeal forms with contact data
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

# Configuration
CRM_BRIDGE_URL = os.getenv('CRM_BRIDGE_URL', 'https://bde-sales-portal.onrender.com')
DOCUSEAL_API_URL = os.getenv('DOCUSEAL_API_URL', 'https://bde-docuseal-selfhosted.onrender.com/api')
DOCUSEAL_API_KEY = os.getenv('DOCUSEAL_API_KEY', '')  # Set this in your .env file

class DocuSealFormPrefill:
    def __init__(self):
        self.crm_bridge_url = CRM_BRIDGE_URL
        self.docuseal_api_url = DOCUSEAL_API_URL
        self.docuseal_api_key = DOCUSEAL_API_KEY
        
    def search_crm_contact(self, search_term: str) -> Optional[Dict]:
        """Search for a contact in the CRM"""
        try:
            response = requests.get(
                f"{self.crm_bridge_url}/api/contacts/search",
                params={'q': search_term}
            )
            response.raise_for_status()
            contacts = response.json()
            
            if contacts:
                return contacts[0]  # Return first match
            return None
        except Exception as e:
            print(f"Error searching CRM: {e}")
            return None
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict]:
        """Get a specific contact by ID"""
        try:
            response = requests.get(f"{self.crm_bridge_url}/api/contacts/{contact_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting contact: {e}")
            return None
    
    def map_crm_to_docuseal_fields(self, contact: Dict) -> Dict:
        """Map CRM contact fields to DocuSeal form fields"""
        # Get custom fields from contact
        custom_fields = contact.get('customFields', {})
        
        # Map CRM fields to DocuSeal field names
        mapped_values = {
            # Business Information
            'business_name': contact.get('companyName', ''),
            'dba': custom_fields.get('DBA', ''),
            'fein': custom_fields.get('FederalTaxID', ''),
            'state_id': custom_fields.get('StateTaxID', ''),
            
            # Address Information
            'billing_address': contact.get('address', {}).get('street', ''),
            'billing_city': contact.get('address', {}).get('city', ''),
            'billing_state': contact.get('address', {}).get('state', ''),
            'billing_zip': contact.get('address', {}).get('zip', ''),
            
            # Contact Information
            'billing_phone': contact.get('phone', ''),
            'billing_fax': custom_fields.get('FaxNumber', ''),
            
            # Business Details
            'years_in_biz': custom_fields.get('YearsInBusiness', ''),
            'number_employees': custom_fields.get('NumberOfEmployees', ''),
            'estimated_ann_diesel': custom_fields.get('AnnualDieselVolume', ''),
            'estimated_ann_unl': custom_fields.get('AnnualGasolineVolume', ''),
            'credit_request': custom_fields.get('CreditAmountRequested', ''),
            
            # Entity Type (this would need custom logic based on your CRM data)
            'corp_structure': self._determine_corp_structure(custom_fields),
            
            # Key Contacts
            'purchase_mgr_name': custom_fields.get('PurchasingManagerName', ''),
            'acct_payable_name': custom_fields.get('AccountsPayableName', ''),
            'purchasing_email': custom_fields.get('PurchasingEmail', ''),
            'purchasing_phone': custom_fields.get('PurchasingPhone', ''),
            'accounts_payable_email': custom_fields.get('AccountsPayableEmail', ''),
            'accounts_payable_phone': custom_fields.get('AccountsPayablePhone', ''),
            
            # Signer Information (from primary contact)
            'signer_name': contact.get('name', ''),
            'signer_title': contact.get('title', ''),
            
            # Date
            'signature_date': datetime.now().strftime('%m/%d/%Y')
        }
        
        # Remove empty values
        return {k: v for k, v in mapped_values.items() if v}
    
    def _determine_corp_structure(self, custom_fields: Dict) -> str:
        """Determine corporation structure from custom fields"""
        entity_type = custom_fields.get('EntityType', '').lower()
        
        if 'llc' in entity_type:
            return 'llc'
        elif 's corp' in entity_type or 's-corp' in entity_type:
            return 's_corp'
        elif 'c corp' in entity_type or 'c-corp' in entity_type:
            return 'c_corp'
        elif 'partnership' in entity_type:
            return 'partnership'
        elif 'sole' in entity_type or 'proprietor' in entity_type:
            return 'sole_proprietor'
        else:
            return 'other'
    
    def create_prefilled_submission(self, template_id: str, contact_id: str, send_email: bool = True) -> Optional[Dict]:
        """Create a DocuSeal submission with pre-filled data from CRM contact"""
        
        # Get contact from CRM
        contact = self.get_contact_by_id(contact_id)
        if not contact:
            print(f"Contact {contact_id} not found")
            return None
        
        # Map fields
        prefilled_values = self.map_crm_to_docuseal_fields(contact)
        
        # Create submission payload
        payload = {
            "template_id": template_id,
            "send_email": send_email,
            "submitters": [
                {
                    "role": "First Party",
                    "email": contact.get('email', ''),
                    "name": contact.get('name', ''),
                    "values": prefilled_values
                }
            ]
        }
        
        # Make API request to DocuSeal
        headers = {
            "X-Auth-Token": self.docuseal_api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.docuseal_api_url}/submissions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating submission: {e}")
            return None
    
    def create_submission_link(self, template_id: str, contact_id: str) -> Optional[str]:
        """Create a submission and return the signing link"""
        submission = self.create_prefilled_submission(template_id, contact_id, send_email=False)
        
        if submission and submission.get('submitters'):
            # Return the first submitter's signing link
            return submission['submitters'][0].get('embed_src')
        
        return None


# Simple web interface for form pre-filling
def create_prefill_interface():
    """Create a simple HTTP server for the pre-fill interface"""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import urllib.parse
    
    class PrefillHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>BDE DocuSeal Form Pre-fill</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .container { max-width: 800px; margin: auto; }
                        input, select { width: 100%; padding: 8px; margin: 5px 0; }
                        button { background: #0066cc; color: white; padding: 10px 20px; border: none; cursor: pointer; }
                        .results { margin-top: 20px; padding: 15px; background: #f5f5f5; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>BDE DocuSeal Form Pre-fill</h1>
                        <h2>Search CRM Contact</h2>
                        <input type="text" id="search" placeholder="Enter company name or contact name">
                        <button onclick="searchContacts()">Search</button>
                        
                        <div id="results"></div>
                        
                        <h2>Select Template</h2>
                        <select id="template">
                            <option value="">Select a template...</option>
                            <option value="CUSTOMER_SETUP_TEMPLATE_ID">Customer Setup Form</option>
                            <option value="EFT_TEMPLATE_ID">EFT Authorization</option>
                            <option value="P66_LOI_TEMPLATE_ID">Phillips 66 LOI</option>
                            <option value="VP_LOI_TEMPLATE_ID">VP Racing LOI</option>
                        </select>
                        
                        <button onclick="createPrefilled()">Create Pre-filled Form</button>
                        
                        <div id="link-result"></div>
                    </div>
                    
                    <script>
                        let selectedContactId = null;
                        
                        async function searchContacts() {
                            const search = document.getElementById('search').value;
                            const response = await fetch(`/search?q=${encodeURIComponent(search)}`);
                            const contacts = await response.json();
                            
                            let html = '<h3>Search Results</h3>';
                            if (contacts.length === 0) {
                                html += '<p>No contacts found</p>';
                            } else {
                                html += '<div class="results">';
                                contacts.forEach(contact => {
                                    html += `
                                        <div style="padding: 10px; border-bottom: 1px solid #ddd;">
                                            <input type="radio" name="contact" value="${contact.id}" 
                                                   onchange="selectedContactId='${contact.id}'">
                                            <strong>${contact.companyName || contact.name}</strong><br>
                                            ${contact.email || ''}<br>
                                            ${contact.phone || ''}
                                        </div>
                                    `;
                                });
                                html += '</div>';
                            }
                            document.getElementById('results').innerHTML = html;
                        }
                        
                        async function createPrefilled() {
                            if (!selectedContactId) {
                                alert('Please select a contact first');
                                return;
                            }
                            
                            const templateId = document.getElementById('template').value;
                            if (!templateId) {
                                alert('Please select a template');
                                return;
                            }
                            
                            const response = await fetch(`/prefill?template=${templateId}&contact=${selectedContactId}`);
                            const result = await response.json();
                            
                            if (result.link) {
                                document.getElementById('link-result').innerHTML = `
                                    <div class="results">
                                        <h3>Pre-filled Form Created!</h3>
                                        <p>Link: <a href="${result.link}" target="_blank">${result.link}</a></p>
                                        <button onclick="navigator.clipboard.writeText('${result.link}')">Copy Link</button>
                                    </div>
                                `;
                            }
                        }
                    </script>
                </body>
                </html>
                '''
                self.wfile.write(html.encode())
                
            elif self.path.startswith('/search'):
                # Parse query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                search_term = params.get('q', [''])[0]
                
                # Search CRM
                prefill = DocuSealFormPrefill()
                contacts = []
                
                # This is a simplified search - you'd implement the actual search
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(contacts).encode())
                
            elif self.path.startswith('/prefill'):
                # Parse query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                template_id = params.get('template', [''])[0]
                contact_id = params.get('contact', [''])[0]
                
                # Create pre-filled form
                prefill = DocuSealFormPrefill()
                link = prefill.create_submission_link(template_id, contact_id)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'link': link}).encode())
    
    return PrefillHandler


if __name__ == "__main__":
    # Example usage
    prefill = DocuSealFormPrefill()
    
    # Example: Search for a contact and create a pre-filled form
    contact = prefill.search_crm_contact("Acme Corp")
    if contact:
        print(f"Found contact: {contact['name']}")
        
        # Create pre-filled submission
        template_id = "YOUR_TEMPLATE_ID"  # Replace with actual template ID
        submission = prefill.create_prefilled_submission(template_id, contact['id'])
        if submission:
            print(f"Created submission: {submission['id']}")
    
    # Start the web interface
    print("Starting pre-fill interface on http://localhost:8005")
    handler = create_prefill_interface()
    server = HTTPServer(('localhost', 8005), handler)
    server.serve_forever()