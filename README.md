# 🔮 GraphRAG with FastAPI, Neo4j & Ollama

A production-ready **Graph Retrieval-Augmented Generation (GraphRAG)** system that combines the power of knowledge graphs with large language models for intelligent question answering.

## 🌟 Features

- **GraphRAG Query Pipeline**: Semantic search → Graph expansion → LLM generation
- **Neo4j Graph Database**: Store and traverse complex knowledge relationships
- **Ollama Integration**: Local LLM processing with Llama 3.2:1b
- **Interactive Visualization**: D3.js-powered graph exploration interface
- **Document Ingestion**: Automatic entity extraction and knowledge graph construction
- **RESTful API**: FastAPI backend with async operations
- **Sample Dataset**: Pre-loaded movie knowledge base for testing

## 🏗️ Architecture

```
┌─────────────┐
│   User UI   │
│  (Browser)  │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────┐
│          FastAPI Application            │
│  ┌────────────┐      ┌───────────────┐ │
│  │  Routers   │      │   Services    │ │
│  │  - Query   │─────▶│  - GraphRAG   │ │
│  │  - Viz     │      │  - Neo4j      │ │
│  └────────────┘      │  - Ollama     │ │
│                      └───────┬───────┘ │
└──────────────────────────────┼─────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                  │
      ┌───────▼────────┐              ┌────────▼────────┐
      │  Neo4j Graph   │              │  Ollama LLM     │
      │   Database     │              │  llama3.2:1b    │
      └────────────────┘              └─────────────────┘
```

## 📋 Prerequisites

- **Python 3.10+**
- **Neo4j** (installed locally or via Docker)
- **Ollama** with llama3.2:1b model
- **Git**

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd /home/bnb/Documents/GraphRAG

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Key settings:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag123
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
```

### 3. Start Services

#### Start Neo4j (via Docker)
```bash
docker-compose up -d
```

Or if Neo4j is already installed locally, ensure it's running on port 7687.

#### Start Ollama
```bash
# Ensure Ollama is running
ollama serve

# Pull the model (if not already available)
ollama pull llama3.2:1b
```

### 4. Initialize Database

```bash
# Create constraints and indices
python scripts/init_db.py

# Load sample movie dataset
python scripts/seed_sample_data.py
```

### 5. Run Application

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the application:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Neo4j Browser**: http://localhost:7474 (if using Docker)

## 📖 Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. Enter a question in the search box:
   - "Who directed The Matrix?"
   - "What movies did Leonardo DiCaprio act in?"
   - "Tell me about Christopher Nolan's films"
   - "What are the best science fiction movies?"
3. View the AI-generated answer with graph context
4. Explore the interactive knowledge graph visualization
5. Examine context nodes and relationships

### API Endpoints

#### Query Knowledge Graph
```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who directed The Matrix?",
    "max_depth": 2,
    "top_k": 10
  }'
```

#### Ingest Document
```bash
curl -X POST "http://localhost:8000/api/query/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "GraphRAG combines graph databases with retrieval-augmented generation...",
    "metadata": {"title": "GraphRAG Overview", "source": "documentation"}
  }'
```

#### Get Graph Statistics
```bash
curl "http://localhost:8000/api/graph/stats"
```

#### Search Nodes
```bash
curl "http://localhost:8000/api/graph/search?label=Movie&limit=10"
```

## 🎬 Sample Dataset

The sample movie dataset includes:

**Movies (5)**:
- The Matrix (1999)
- Inception (2010)
- Interstellar (2014)
- The Dark Knight (2008)
- Pulp Fiction (1994)

**People (8)**:
- Actors: Keanu Reeves, Leonardo DiCaprio, Matthew McConaughey, Christian Bale, John Travolta
- Directors: Lana Wachowski, Christopher Nolan, Quentin Tarantino

**Genres (5)**:
- Science Fiction, Action, Thriller, Drama, Crime

**Relationships**:
- ACTED_IN (with character names)
- DIRECTED
- HAS_GENRE

## 🔧 Configuration

### GraphRAG Parameters

Edit [.env](.env) or pass in API requests:

- `MAX_SEARCH_RESULTS` (default: 10) - Number of relevant nodes to retrieve
- `MAX_GRAPH_DEPTH` (default: 2) - How far to traverse from seed nodes
- `CHUNK_SIZE` (default: 500) - Document chunk size for ingestion
- `CHUNK_OVERLAP` (default: 50) - Overlap between chunks

### Ollama Model

To use a different model:

```bash
# Pull a different model
ollama pull llama3:8b

# Update .env
OLLAMA_MODEL=llama3:8b
```

## 📁 Project Structure

```
GraphRAG/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── routers/
│   │   ├── query.py            # Query endpoints
│   │   └── visualization.py    # Visualization endpoints
│   ├── services/
│   │   ├── neo4j_service.py    # Neo4j operations
│   │   ├── ollama_service.py   # Ollama LLM integration
│   │   └── graphrag_service.py # GraphRAG pipeline
│   ├── templates/
│   │   ├── graph_view.html     # Main UI template
│   │   └── components/
│   │       └── node_card.html  # Node display component
│   └── static/
│       ├── css/
│       │   └── styles.css      # Application styles
│       └── js/
│           └── graph_vis.js    # D3.js visualization
├── scripts/
│   ├── init_db.py              # Database initialization
│   └── seed_sample_data.py     # Sample data loader
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Neo4j container config
├── .env.example                # Example environment
└── README.md                   # This file
```

## 🔍 How GraphRAG Works

### Query Pipeline

1. **Query Embedding**: Convert user question to vector using Ollama
2. **Semantic Search**: Find most relevant nodes using cosine similarity
3. **Graph Expansion**: Traverse relationships to gather context
4. **Context Formatting**: Structure graph data for LLM
5. **Answer Generation**: LLM generates answer based on graph context

### Document Ingestion

1. **Chunking**: Split document into manageable pieces
2. **Embedding**: Generate embeddings for each chunk
3. **Entity Extraction**: Use LLM to identify entities and relationships
4. **Graph Storage**: Store nodes and relationships in Neo4j

## 🛠️ Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black app/ scripts/

# Lint
flake8 app/ scripts/
```

### Debugging

Enable debug logging:

```python
# In app/main.py
logging.basicConfig(level=logging.DEBUG)
```

## 🐛 Troubleshooting

### Neo4j Connection Issues

```bash
# Check Neo4j is running
docker ps | grep neo4j

# View Neo4j logs
docker logs graphrag-neo4j

# Test connection
cypher-shell -a bolt://localhost:7687 -u neo4j -p graphrag123
```

### Ollama Issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test model
ollama run llama3.2:1b "Hello, world!"

# View Ollama logs
journalctl -u ollama -f  # On systemd systems
```

### API Errors

Check health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "ollama_connected": true
}
```

## 🚀 Production Deployment

### Environment Variables

Set secure credentials:
```env
NEO4J_PASSWORD=<strong-password>
APP_RELOAD=false
```

### Run with Gunicorn

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

Add application to docker-compose.yml:

```yaml
graphrag-app:
  build: .
  ports:
    - "8000:8000"
  depends_on:
    - neo4j
  environment:
    - NEO4J_URI=bolt://neo4j:7687
```

## 📚 API Documentation

Full API documentation available at: http://localhost:8000/docs

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query/` | Query knowledge graph |
| POST | `/api/query/ingest` | Ingest document |
| GET | `/api/graph/stats` | Graph statistics |
| GET | `/api/graph/node/{id}` | Get node details |
| GET | `/api/graph/neighbors/{id}` | Get neighbors |
| GET | `/api/graph/search` | Search nodes |
| DELETE | `/api/graph/clear` | Clear database |
| GET | `/health` | Health check |
| GET | `/` | Web UI |

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - feel free to use this project for learning and development.

## 🙏 Acknowledgments

- **Neo4j** - Graph database platform
- **Ollama** - Local LLM inference
- **FastAPI** - Modern Python web framework
- **D3.js** - Graph visualization library

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check [Neo4j documentation](https://neo4j.com/docs/)
- Check [Ollama documentation](https://ollama.ai/docs)
- Check [FastAPI documentation](https://fastapi.tiangolo.com/)

---

**Built with ❤️ using GraphRAG, Neo4j, and Ollama**
