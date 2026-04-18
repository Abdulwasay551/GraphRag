#!/bin/bash

# GraphRAG Setup Script
echo "🔮 Setting up GraphRAG Project..."
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure Neo4j is running (or run: docker-compose up -d)"
echo "2. Ensure Ollama is running with llama3.2:1b"
echo "3. Initialize database: python scripts/init_db.py"
echo "4. Seed sample data: python scripts/seed_sample_data.py"
echo "5. Start the app: uvicorn app.main:app --reload"
echo ""
echo "Then open http://localhost:8000 in your browser!"
