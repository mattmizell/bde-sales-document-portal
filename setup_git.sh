#!/bin/bash
# Git setup script for BDE Sales Document Portal

echo "🚀 Setting up Git repository for BDE Sales Document Portal"

# Initialize Git repository
git init

# Add remote repository
git remote add origin https://github.com/mattmizell/bde_sales_docs.git

# Configure Git (update with your details)
git config user.name "Matt Mizell"
git config user.email "matt@betterdayenergy.com"

# Create initial commit
git add .
git commit -m "Initial commit: Clean BDE Sales Document Portal with DocuSeal integration

Features:
- Clean FastAPI architecture
- DocuSeal external service integration
- Professional e-signature workflow
- PostgreSQL database with optimized models
- Email notification system
- Webhook handling for document completion
- Multi-document support (P66 LOI, VP Racing LOI, EFT, Customer Setup)

No legacy canvas signature code - built for production from day one."

# Push to GitHub
echo "📤 Pushing to GitHub repository..."
git branch -M main
git push -u origin main

echo "✅ Git repository setup complete!"
echo "🌐 Repository: https://github.com/mattmizell/bde_sales_docs.git"