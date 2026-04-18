# Quick Start Guide

## Installation & Setup

```bash
# 1. Run setup script
./setup.sh

# OR manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Start Services

```bash
# Start Neo4j (Docker)
docker-compose up -d

# Or use your installed Neo4j
# Make sure it's running on bolt://localhost:7687

# Verify Ollama is running
ollama list
ollama run llama3.2:1b "test"
```

## Initialize Database

```bash
# Create database schema
python scripts/init_db.py

# Load sample movie data
python scripts/seed_sample_data.py
```

## Run Application

```bash
# Start FastAPI server
uvicorn app.main:app --reload

# Or
python -m app.main
```

## Access Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, pass: graphrag123)

## Sample Queries

Try these questions in the web interface:

1. **"Who directed The Matrix?"**
2. **"What movies did Leonardo DiCaprio act in?"**
3. **"Tell me about Christopher Nolan's films"**
4. **"What are the best science fiction movies?"**
5. **"Who played Batman in The Dark Knight?"**
6. **"What genre is Pulp Fiction?"**
7. **"Which movies are science fiction?"**

## Testing the API

```bash
# Query endpoint
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "Who directed The Matrix?", "max_depth": 2, "top_k": 10}'

# Get stats
curl http://localhost:8000/api/graph/stats

# Health check
curl http://localhost:8000/health
```

## Troubleshooting

### Neo4j not connecting
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs graphrag-neo4j

# Restart
docker-compose restart neo4j
```

### Ollama not responding
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama  # or restart manually
```

### Database is empty
```bash
# Re-seed the database
python scripts/seed_sample_data.py
```

## Project Structure

```
GraphRAG/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── services/            # Business logic
│   │   ├── neo4j_service.py
│   │   ├── ollama_service.py
│   │   └── graphrag_service.py
│   ├── routers/             # API endpoints
│   ├── models/              # Pydantic schemas
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS/JS
├── scripts/
│   ├── init_db.py           # Database setup
│   └── seed_sample_data.py  # Sample data
└── requirements.txt
```

## Common Commands

```bash
# Activate venv
source venv/bin/activate

# Install new package
pip install <package>
pip freeze > requirements.txt

# Run tests
pytest tests/

# Clear database
curl -X DELETE http://localhost:8000/api/graph/clear
python scripts/seed_sample_data.py
```

## Configuration

Edit `.env` file:

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag123

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# GraphRAG
MAX_SEARCH_RESULTS=10
MAX_GRAPH_DEPTH=2
```

## Next Steps

1. ✅ Basic setup complete
2. 🔍 Explore the sample dataset
3. 📝 Try different queries
4. 📊 View graph visualizations
5. 🚀 Add your own data
6. 🎯 Customize for your use case
