# 🚀 GraphRAG SaaS Platform - Quick Start

## What's New in Version 2.0?

Your GraphRAG project has been transformed into a **production-ready multi-tenant SaaS platform**!

### 🎯 Major New Features

1. **🔐 Authentication & User Management** - JWT-based auth, user registration, workspaces
2. **📁 Document Upload** - Support for PDF, DOCX, CSV, Excel, JSON, Markdown, HTML
3. **🎨 Custom Schema Builder** - Define your own entity and relationship types
4. **💬 Embeddable Chatbot Widget** - Drop-in JavaScript widget for any website
5. **📤 Export Functionality** - Export graphs in JSON, CSV, GraphML, Cypher formats
6. **🏢 Multi-Tenancy** - Complete workspace isolation with resource limits

---

## ⚡ Quick Installation

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup_saas.sh
```

This will:
- Create virtual environment
- Install all dependencies
- Generate secure JWT secret
- Create .env file
- Check service status

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p uploads

# Copy and edit .env
cp .env.example .env
nano .env

# Generate secure JWT secret
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

---

## 🏃 Running the Application

### 1. Start Required Services

**Neo4j:**
```bash
docker-compose up -d
```

**Ollama:**
```bash
ollama serve
```

**Redis:**
```bash
# Option 1: Docker
docker run -d --name redis -p 6379:6379 redis:alpine

# Option 2: System service
sudo systemctl start redis
```

### 2. Initialize Database

```bash
python scripts/init_db.py
```

### 3. Start Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Application

- **API Documentation**: http://localhost:8000/docs
- **Web Interface**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

---

## 📚 API Examples

### Register a User

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/documents/upload?workspace_id=WORKSPACE_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

### Query Knowledge Graph

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is GraphRAG?",
    "max_depth": 2,
    "top_k": 10
  }'
```

### Export Graph

```bash
curl -X POST "http://localhost:8000/api/export/WORKSPACE_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json"
  }'
```

---

## 🎨 Embed the Chatbot

1. Get your workspace settings:
```bash
curl -X GET "http://localhost:8000/api/chatbot/WORKSPACE_ID/settings" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. Copy the embed code and paste before `</body>` in your HTML:

```html
<script>
  (function() {
    var chatbotConfig = {
      workspaceId: 'your-workspace-id',
      apiKey: 'your-api-key',
      apiUrl: 'http://localhost:8000',
      title: 'AI Assistant',
      primaryColor: '#3B82F6'
    };
    var script = document.createElement('script');
    script.src = chatbotConfig.apiUrl + '/static/embed/chatbot.js';
    script.async = true;
    script.onload = function() {
      GraphRAGChatbot.init(chatbotConfig);
    };
    document.head.appendChild(script);
  })();
</script>
```

---

## 📖 Documentation

- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Detailed migration from v1 to v2
- **[FEATURES.md](FEATURES.md)** - Complete feature documentation
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Implementation summary
- **API Docs** - Available at http://localhost:8000/docs

---

## 🎯 Supported File Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| PDF | .pdf | PyPDF2 |
| Word | .docx, .doc | python-docx |
| Text | .txt | Native |
| CSV | .csv | pandas |
| Excel | .xlsx, .xls | pandas + openpyxl |
| JSON | .json | Native |
| Markdown | .md | markdown |
| HTML | .html, .htm | BeautifulSoup |

---

## 💰 Workspace Plans

| Plan | Max Nodes | Max Workspaces | Price |
|------|-----------|----------------|-------|
| Free | 1,000 | 1 | $0 |
| Pro | 50,000 | 10 | $29/mo |
| Enterprise | Unlimited | Unlimited | Custom |

---

## 🔧 Configuration

Key environment variables in `.env`:

```env
# Security
JWT_SECRET_KEY=your-secret-key

# Services
NEO4J_URI=bolt://localhost:7687
OLLAMA_BASE_URL=http://localhost:11434
REDIS_HOST=localhost

# Upload Limits
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=./uploads

# Workspace Limits
FREE_PLAN_MAX_NODES=1000
PRO_PLAN_MAX_NODES=50000
```

---

## 🐛 Troubleshooting

### Authentication Errors
```
Error: "Could not validate credentials"
```
**Solution**: Token expired. Login again to get new token.

### Document Upload Fails
```
Error: "File type not supported"
```
**Solution**: Check file extension. Supported: pdf, docx, txt, csv, json, xlsx, md, html

### Redis Connection Error
```
Error: "Cannot connect to Redis"
```
**Solution**: Start Redis with `docker run -d --name redis -p 6379:6379 redis:alpine`

---

## 📞 Support

- **GitHub Issues**: [Your Repository]
- **Documentation**: http://localhost:8000/docs
- **Email**: support@yourdomain.com

---

## 🎉 What's Next?

1. **Build Frontend UI** - React/Vue/Svelte interfaces for new features
2. **Add Email Verification** - User registration confirmation
3. **Integrate Stripe** - Payment processing for Pro/Enterprise plans
4. **Add Team Features** - Invite users to workspaces
5. **Build Analytics Dashboard** - Usage statistics and insights

---

## ⭐ Key Features at a Glance

✅ JWT Authentication  
✅ Multi-tenant Workspaces  
✅ 8 Document Formats  
✅ Custom Entity Types  
✅ Embeddable Chatbot  
✅ 4 Export Formats  
✅ RESTful API  
✅ Background Processing  
✅ Resource Limits  
✅ API Key Management  

**Ready for production deployment!** 🚀
