#!/bin/bash
# Quick Deployment Script for Order-to-Cash System

set -e

echo "🚀 Order-to-Cash System - Quick Deployment"
echo "=========================================="
echo ""
echo "Select your deployment platform:"
echo "1) Render (Recommended - Free)"
echo "2) Railway (Free $5/month)"
echo "3) Heroku (Paid - $7/month)"
echo "4) Docker (Local testing)"
echo ""

read -p "Enter number (1-4): " platform

case $platform in
  1)
    echo ""
    echo "📋 RENDER DEPLOYMENT"
    echo "==================="
    echo "1. Go to https://render.com"
    echo "2. Sign up with GitHub"
    echo "3. Click 'New +' → 'Web Service'"
    echo "4. Connect this GitHub repository"
    echo "5. Set Runtime: Docker"
    echo "6. Add environment variable:"
    echo "   GROQ_API_KEY=your_groq_api_key"
    echo "7. Click 'Deploy'"
    echo ""
    echo "✅ Your app will be live in 2-3 minutes!"
    echo "Access at: https://your-service-name.onrender.com"
    ;;
  2)
    echo ""
    echo "📋 RAILWAY DEPLOYMENT"
    echo "===================="
    echo "1. Go to https://railway.app"
    echo "2. Click 'New Project' → 'Deploy from GitHub repo'"
    echo "3. Select this repository"
    echo "4. Add variables in Railway dashboard:"
    echo "   GROQ_API_KEY=your_groq_api_key"
    echo "5. Deploy button will appear"
    echo ""
    echo "✅ Your app will be live shortly!"
    echo "Access at: https://your-railway-domain.railway.app"
    ;;
  3)
    echo ""
    echo "📋 HEROKU DEPLOYMENT"
    echo "===================="
    echo "1. Install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli"
    echo "2. Run: heroku login"
    echo "3. Run: heroku create your-app-name"
    echo "4. Run: heroku config:set GROQ_API_KEY=your_groq_api_key"
    echo "5. Run: git push heroku main"
    echo ""
    echo "✅ Your app will be live on Heroku!"
    echo "Access at: https://your-app-name.herokuapp.com"
    ;;
  4)
    echo ""
    echo "🐳 DOCKER LOCAL DEPLOYMENT"
    echo "=========================="
    if ! command -v docker &> /dev/null; then
      echo "❌ Docker not installed!"
      echo "Install from: https://www.docker.com/products/docker-desktop"
      exit 1
    fi
    echo ""
    echo "Building and starting Docker container..."
    docker compose up
    echo ""
    echo "✅ App is running locally!"
    echo "Access at: http://localhost:8000"
    ;;
  *)
    echo "❌ Invalid choice!"
    exit 1
    ;;
esac

echo ""
echo "💡 For more details, see DEPLOYMENT.md"
echo "🎯 For complete setup, see BUILD_READY.md"
