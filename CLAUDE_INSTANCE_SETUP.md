# Claude Instance Setup Guide

**Complete reference for new Claude instances working on BDE Sales Document Portal**

## 🎯 Project Overview

### **What This Is**
- **Clean, modern document signing portal** for Better Day Energy
- **DocuSeal integration** for professional e-signatures
- **Two-stage workflow**: Sales person initiates → Customer completes & signs
- **Production-ready architecture** with no legacy code

### **What This Replaces**
- Previous v1 system with canvas signatures (archived in backup)
- Custom signature handling (replaced with DocuSeal)
- Complex form validation (simplified with external service)

## 🏗️ Architecture Understanding

### **Service Structure**
```
Main App (FastAPI)     DocuSeal (Ruby/Rails)
├── Customer data      ├── Document templates
├── Workflow tracking  ├── Signature collection
├── Email notifications├── ESIGN compliance
└── API endpoints      └── PDF generation
```

### **Data Flow**
1. **Sales person** creates customer in main app
2. **Main app** calls DocuSeal API to create submission
3. **DocuSeal** sends email with signing link to customer
4. **Customer** signs document via DocuSeal interface
5. **DocuSeal** sends webhook to main app on completion
6. **Main app** sends completion notification to sales person

## 📁 Project Structure

### **Key Files to Understand**
```
main.py                   # Core FastAPI application
database/models.py        # Clean database models
services/docuseal_client.py # DocuSeal API integration
services/email_service.py    # Email notifications
.env                     # Production credentials
CREDENTIALS_DOCUMENTATION.md # All secrets and keys
render.yaml              # Deployment configuration
```

### **Important Concepts**
- **DocumentWorkflow**: Tracks each signing process
- **Customer**: Basic customer information
- **WorkflowEvent**: Audit trail of all actions
- **EmailLog**: Email delivery tracking

## 🔐 Credentials and Access

### **Critical Accounts**
```
Gmail: transaction.coordinator.agent@gmail.com
App Password: xmvi xvso zblo oewe
CRM API Key: 1073223-4036284360051868673733029852600-hzOnMMgwOvTV86XHs9c4H3gF5I7aTwO33PJSRXk9yQT957IY1W
Grok API: xai-730cElC0cSJcQ8KgbpaMZ32MrwhV1m563LNfxWr5zgc9UTkwBr2pYm36s86948sPHcJf8yH6rw9AgQUi
```

### **Service URLs (After Deployment)**
```
Main App: https://bde-sales-document-portal.onrender.com
DocuSeal: https://bde-docuseal-service.onrender.com
API Docs: https://bde-sales-document-portal.onrender.com/docs
Health: https://bde-sales-document-portal.onrender.com/health
```

## 🚀 Deployment Process

### **Current Status**
- ✅ **Code complete** - All files created in target directory
- ✅ **Credentials documented** - All secrets identified
- ✅ **Deployment config ready** - render.yaml for both services
- 🔄 **Ready for Git setup** - Need to run setup_git.sh
- 🔄 **Ready for deployment** - Push to GitHub → Deploy to Render

### **Next Steps for Deployment**
1. **Setup Git repository**:
   ```bash
   cd /home/mattmizell/PycharmProjects/bde_sales_document_portal
   chmod +x setup_git.sh
   ./setup_git.sh
   ```

2. **Deploy to Render**:
   - Use render.yaml for automatic deployment
   - Creates both main app and DocuSeal service
   - Includes PostgreSQL databases

3. **Configure DocuSeal**:
   - Wait for deployment completion
   - Access DocuSeal dashboard
   - Generate API token
   - Update main app environment variables

## 🔧 Development Workflow

### **Local Development**
```bash
# Setup local environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure local database
createdb sales_portal_dev
export DATABASE_URL="postgresql://mattmizell:training1@localhost:5432/sales_portal_dev"

# Run application
uvicorn main:app --reload --port 8000
```

### **Testing Integration**
```bash
# Test email connection
python -c "from services.email_service import EmailService; print(EmailService(...).test_connection())"

# Test DocuSeal connection (after deployment)
curl -H "X-Auth-Token: your_token" https://bde-docuseal-service.onrender.com/api/templates
```

## 📋 Common Tasks

### **Adding New Document Types**
1. **Create DocuSeal template** via API or dashboard
2. **Add template configuration** to database
3. **Update workflow types** in models
4. **Add API endpoint** for new document type
5. **Test end-to-end** workflow

### **Debugging Issues**
1. **Check health endpoint**: `/health` shows all service status
2. **Review logs**: Render dashboard shows application logs
3. **Test individual services**: 
   - Database connection
   - DocuSeal API
   - Email delivery
   - Webhook reception

### **Monitoring Production**
- **Health checks**: Automated monitoring via `/health`
- **Email delivery**: Check SMTP logs and delivery status
- **DocuSeal status**: Monitor external service availability
- **Database performance**: Render provides metrics

## 🛠️ Troubleshooting Guide

### **Common Issues**
1. **DocuSeal not responding**: Check service deployment, API token
2. **Email not sending**: Verify Gmail app password, SMTP settings
3. **Database connection errors**: Check DATABASE_URL configuration
4. **Webhook not working**: Verify webhook URL in DocuSeal settings

### **Emergency Procedures**
1. **Service down**: Check Render dashboard, restart if needed
2. **DocuSeal issues**: Can deploy new instance, update API token
3. **Email problems**: Can switch to different SMTP provider
4. **Database issues**: Render provides automatic backups

## 🎯 Key Success Metrics

### **Technical Metrics**
- **API response time**: < 500ms for most endpoints
- **Email delivery rate**: > 95% successful delivery
- **Document completion rate**: Track via workflow events
- **Service uptime**: > 99% availability

### **Business Metrics**
- **Document turnaround time**: Sales initiation to customer completion
- **Error rate**: Failed document creations or deliveries
- **Customer experience**: Time to complete signing process

## 📝 Important Notes for Claude

### **Don't Reinvent**
- ✅ **Use DocuSeal** for all signature needs (don't build custom)
- ✅ **Follow established patterns** in the codebase
- ✅ **Leverage existing integrations** (email, CRM, database)

### **Focus Areas**
- **API development**: Adding new endpoints as needed
- **Integration improvements**: Better error handling, retry logic
- **Monitoring**: Enhanced logging and alerting
- **Frontend**: Building dashboard/UI on top of API

### **Avoid**
- ❌ **Custom signature implementation** (use DocuSeal)
- ❌ **Major architectural changes** (current design is clean)
- ❌ **Credential changes** without documenting

## 🎉 Success Criteria

### **Deployment Success**
- [ ] Both services deployed and accessible
- [ ] Health check returns "healthy" for all services
- [ ] Can create customer via API
- [ ] Can initiate document signing
- [ ] Email delivery works
- [ ] Customer can complete signing
- [ ] Webhook notifications received

### **Production Ready**
- [ ] All credentials properly configured
- [ ] Monitoring and logging in place
- [ ] Error handling robust
- [ ] Performance acceptable
- [ ] Documentation complete

---

**🎯 Result**: Professional document signing portal ready for Better Day Energy sales team with zero legacy baggage.**