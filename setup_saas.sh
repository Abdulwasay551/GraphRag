#!/bin/bash

# GraphRAG SaaS Platform - Quick Setup Script
# This script installs all dependencies and sets up the environment

echo "🚀 Setting up GraphRAG SaaS Platform..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads
mkdir -p app/static/embed
echo "✅ Directories created"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag123
NEO4J_DATABASE=neo4j

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_TIMEOUT=120

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
APP_RELOAD=true

# GraphRAG Configuration
MAX_SEARCH_RESULTS=10
MAX_GRAPH_DEPTH=2
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Authentication & Security
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# File Upload Configuration
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50

# Workspace Limits
FREE_PLAN_MAX_NODES=1000
PRO_PLAN_MAX_NODES=50000
ENTERPRISE_PLAN_MAX_NODES=-1
EOF
    echo "✅ .env file created with secure JWT secret"
else
    echo "⚠️  .env file already exists - skipping"
fi

# Check if Neo4j is running
echo ""
echo "🔍 Checking services..."

# Check Neo4j
if curl -s http://localhost:7474 > /dev/null 2>&1; then
    echo "✅ Neo4j is running"
else
    echo "⚠️  Neo4j is not running. Start it with: docker-compose up -d"
fi

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama is not running. Start it with: ollama serve"
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
elif docker ps | grep redis > /dev/null 2>&1; then
    echo "✅ Redis is running (Docker)"
else
    echo "⚠️  Redis is not running. Start it with: docker run -d --name redis -p 6379:6379 redis:alpine"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "📖 Next steps:"
echo "1. Make sure Neo4j, Ollama, and Redis are running"
echo "2. Initialize the database: python scripts/init_db.py"
echo "3. (Optional) Seed sample data: python scripts/seed_sample_data.py"
echo "4. Start the server: uvicorn app.main:app --reload"
echo ""
echo "📚 Documentation:"
echo "- API Docs: http://localhost:8000/docs"
echo "- Migration Guide: MIGRATION_GUIDE.md"
echo "- Features: FEATURES.md"
echo "- Implementation Summary: IMPLEMENTATION_COMPLETE.md"
echo ""
echo "🎉 Happy building!"
