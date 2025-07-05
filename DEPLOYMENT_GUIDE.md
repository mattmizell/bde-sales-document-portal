# BDE Sales Document Portal - Deployment Guide

**Clean, Professional Document Signing Solution with DocuSeal Integration**

## 🎯 Architecture Overview

```
┌─────────────────────┐    API Calls    ┌─────────────────────┐
│                     │ ───────────────> │                     │
│  FastAPI Portal     │                 │    DocuSeal         │
│  (Our Application)  │ <─────────────── │    (E-Signatures)   │
│                     │    Webhooks     │                     │
└─────────────────────┘                 └─────────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────┐                 ┌─────────────────────┐
│  PostgreSQL DB      │                 │   DocuSeal DB       │
│  (Workflow Data)    │                 │   (Signatures)      │
└─────────────────────┘                 └─────────────────────┘
```

## 🚀 Step 1: Deploy to Render.com

### Option A: Deploy from GitHub (Recommended)

1. **Push Code to GitHub**
   ```bash
   cd /home/mattmizell/PycharmProjects/bde_sales_document_portal
   chmod +x setup_git.sh
   ./setup_git.sh
   ```

2. **Deploy Both Services on Render**
   - Go to: https://render.com/dashboard
   - Click "New +" → "Blueprint"
   - Connect: `https://github.com/mattmizell/bde_sales_docs.git`
   - This will deploy BOTH services from the `render.yaml` file:
     - `bde-sales-document-portal` (our FastAPI app)
     - `bde-docuseal-service` (DocuSeal signing service)

### Option B: Manual Service Creation

If Blueprint doesn't work, create services manually:

1. **Create DocuSeal Service**
   ```
   Name: bde-docuseal-service
   Runtime: Docker
   Repository: https://github.com/docusealco/docuseal.git
   Branch: main
   ```

2. **Create Main Application Service**
   ```
   Name: bde-sales-document-portal
   Runtime: Python 3
   Repository: https://github.com/mattmizell/bde_sales_docs.git
   Branch: main
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

## 🔧 Step 2: Configure Environment Variables

### For DocuSeal Service:
```
SECRET_KEY_BASE = [Generate]
RAILS_ENV = production
DATABASE_URL = [From PostgreSQL database]
FORCE_SSL = false
HOST = bde-docuseal-service.onrender.com
```

### For Main Application:
```
DATABASE_URL = [From PostgreSQL database]
DOCUSEAL_URL = https://bde-docuseal-service.onrender.com
DOCUSEAL_API_TOKEN = [Get from DocuSeal dashboard after setup]
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USERNAME = transaction.coordinator.agent@gmail.com
SMTP_PASSWORD = xmvi xvso zblo oewe
FROM_EMAIL = transaction.coordinator.agent@gmail.com
SECRET_KEY = [Generate]
BASE_URL = https://bde-sales-document-portal.onrender.com
```

## 📋 Step 3: Initial Setup

### 3.1 Setup DocuSeal
1. **Wait for DocuSeal deployment** (~5-10 minutes)
2. **Visit DocuSeal dashboard**: https://bde-docuseal-service.onrender.com
3. **Create admin account**
4. **Generate API token**: Settings → API Settings → Generate Token
5. **Copy token** and add to main application environment variables

### 3.2 Test Main Application
1. **Wait for main app deployment** (~3-5 minutes)
2. **Visit health check**: https://bde-sales-document-portal.onrender.com/health
3. **Check API docs**: https://bde-sales-document-portal.onrender.com/docs

## 🧪 Step 4: Test the Integration

### 4.1 Create Test Templates
Use the FastAPI docs interface to create templates:

```json
POST /api/v1/templates
{
  "template_name": "EFT Authorization Test",
  "template_type": "eft_form",
  "html_content": "<div>Test EFT Form</div>",
  "description": "Test template for EFT authorization"
}
```

### 4.2 Test Document Workflow
1. **Create customer** via API
2. **Initiate document** signing
3. **Check email** for signing link
4. **Complete signature** process
5. **Verify webhook** notification

## 🔄 Step 5: Production Configuration

### 5.1 Configure Webhooks
In DocuSeal dashboard:
- Go to Settings → Webhooks
- Add webhook URL: `https://bde-sales-document-portal.onrender.com/api/v1/webhooks/docuseal`
- Select events: `form.completed`, `form.viewed`, `form.started`

### 5.2 Create Production Templates
Create templates for each document type:
- P66 Letter of Intent
- VP Racing Letter of Intent  
- EFT Authorization Form
- Customer Setup Form

## 📊 Step 6: Monitoring and Maintenance

### Health Checks
- **Main App**: https://bde-sales-document-portal.onrender.com/health
- **DocuSeal**: https://bde-docuseal-service.onrender.com

### Logging
- Monitor Render service logs
- Check application health endpoints
- Review webhook delivery status

### Database Management
- PostgreSQL databases auto-managed by Render
- Regular backups handled by Render
- Monitor database performance in dashboard

## 🎉 Expected Results

After successful deployment:

### ✅ Working Features
- **Professional E-Signatures**: Full ESIGN compliance via DocuSeal
- **Two-Stage Workflow**: Sales person initiates → Customer completes
- **Email Automation**: Automatic delivery and notifications
- **Real-time Status**: Live workflow tracking
- **Clean API**: RESTful endpoints for all operations
- **Dashboard Ready**: API endpoints for frontend integration

### 🌐 Service URLs
- **Main Application**: https://bde-sales-document-portal.onrender.com
- **DocuSeal Service**: https://bde-docuseal-service.onrender.com
- **API Documentation**: https://bde-sales-document-portal.onrender.com/docs
- **Health Check**: https://bde-sales-document-portal.onrender.com/health

## 🛠️ Troubleshooting

### Common Issues
1. **DocuSeal not accessible**: Wait longer, check logs
2. **API token invalid**: Regenerate in DocuSeal dashboard
3. **Database connection errors**: Verify DATABASE_URL variables
4. **Webhook not working**: Check webhook URL configuration

### Support
- Check service logs in Render dashboard
- Use health check endpoints for diagnostics
- Monitor email delivery for notifications

---

**🎯 Result**: Professional document signing portal with zero legacy code, full ESIGN compliance, and production-ready architecture from day one.