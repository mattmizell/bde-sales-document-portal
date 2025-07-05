# BDE Sales Document Portal

**Clean, Modern Document Signing Solution with DocuSeal Integration**

## Overview
Professional document signing portal for Better Day Energy sales team. Built with FastAPI + DocuSeal for ESIGN-compliant document workflows.

## Architecture
```
┌─────────────────┐    API Calls    ┌─────────────────┐
│                 │ ───────────────> │                 │
│   FastAPI App   │                 │    DocuSeal     │
│ (Sales Portal)  │ <─────────────── │   (E-Signing)   │
│                 │    Webhooks     │                 │
└─────────────────┘                 └─────────────────┘
        │                                   │
        ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  PostgreSQL     │                 │ DocuSeal DB     │
│  (Form Data)    │                 │ (Signatures)    │
└─────────────────┘                 └─────────────────┘
```

## Features
- ✅ **Professional E-Signatures** - DocuSeal integration with full ESIGN compliance
- ✅ **Multi-Form Support** - P66 LOI, VP Racing LOI, EFT Authorization, Customer Setup
- ✅ **Two-Stage Workflow** - Sales person initiates → Customer completes & signs
- ✅ **Email Automation** - Automatic email delivery with signing links
- ✅ **Real-time Status** - Live tracking of document completion
- ✅ **Webhook Integration** - Instant notifications on document completion
- ✅ **Clean Architecture** - Modern FastAPI backend with external signing service

## Technology Stack
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **E-Signatures**: DocuSeal (external service)
- **Deployment**: Render.com
- **Email**: SMTP integration

## Quick Start

### 1. Deploy DocuSeal Service
```bash
# Follow deployment guide to set up DocuSeal on Render
# Creates separate signing service
```

### 2. Deploy Main Application
```bash
# Deploy FastAPI app to Render
# Connects to DocuSeal via API
```

### 3. Configure Integration
```bash
# Set DocuSeal API credentials
# Configure webhook endpoints
# Test document workflow
```

## Document Types Supported
1. **P66 Letter of Intent** - Phillips 66 fuel supply agreements
2. **VP Racing Letter of Intent** - VP Racing fuel supply agreements  
3. **EFT Authorization** - Electronic funds transfer setup
4. **Customer Setup** - New customer onboarding documents

## Development Status
🚀 **Clean Architecture Implementation**
- Starting fresh with proven DocuSeal integration
- No legacy canvas signature code
- Modern, maintainable codebase
- Full ESIGN compliance from day one

## Previous Versions
- **v1**: Custom canvas signatures (archived in backup)
- **v2**: DocuSeal integration (current clean implementation)

---
**Better Day Energy - Sales Document Portal v2**  
*Professional document signing made simple*