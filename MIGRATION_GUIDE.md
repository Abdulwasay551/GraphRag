# GraphRAG SaaS Platform Migration Guide

## 🎯 Overview

This document guides you through the transition from the single-user GraphRAG demo to a full-featured multi-tenant SaaS platform.

## 🆕 What's New

### 1. **Authentication & User Management**
- JWT-based authentication
- User registration and login
- Secure password hashing with bcrypt
- Protected API endpoints

### 2. **Multi-Tenancy & Workspaces**
- Workspace-based data isolation
- Multiple workspaces per user
- Role-based access control (Owner, Admin, Editor, Viewer)
- Workspace-specific API keys for embedding

### 3. **Document Upload & Processing**
- Support for multiple file formats:
  - PDF, Word (DOCX), Text files
  - CSV, Excel (XLSX/XLS), JSON
  - Markdown, HTML
- Background processing with status tracking
- File size limits and validation
- Automatic text extraction and parsing

### 4. **Custom Schema Builder**
- Define custom entity types with properties
- Define custom relationship types
- Color-coded entity visualization
- Per-workspace schema management

### 5. **Embeddable Chatbot Widget**
- Standalone JavaScript widget
- Customizable appearance (colors, position, messages)
- API key-based authentication for public embedding
- Copy-paste embed code generation

### 6. **Export Functionality**
- Export graphs in multiple formats:
  - JSON (nodes + relationships)
  - CSV (tabular data)
  - GraphML (standard graph format)
  - Cypher (Neo4j query language)
- Filter by labels and relationship types
- Downloadable export files

### 7. **Enhanced Security**
- JWT token authentication
- API key management
- Workspace-level access control
- Rate limiting ready (Redis integration)

## 📦 Installation

### Prerequisites

Install new dependencies:

```bash
# Update pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### New Dependencies Added:
- `python-jose[cryptography]` - JWT tokens
- `passlib[bcrypt]` - Password hashing
- `pypdf2, python-docx, pandas, openpyxl` - Document parsing
- `celery, redis` - Background task processing
- `strawberry-graphql` - GraphQL API (future)
- `markdown, beautifulsoup4, lxml` - HTML/Markdown parsing

### Setup Redis (for Background Tasks)

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Or using Docker
docker run -d --name redis -p 6379:6379 redis:alpine
```

### Update Environment Variables

Add to your `.env` file:

```env
# Authentication & Security
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
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
```

## 🚀 Getting Started

### 1. Initialize Database with New Schema

The new multi-tenant architecture requires additional constraints:

```bash
python scripts/init_db.py
```

This creates constraints for:
- User nodes (unique email)
- Workspace nodes (unique id)
- APIKey nodes (unique key)
- Document nodes (unique id)
- EntityType and RelationshipType nodes

### 2. Start the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Register Your First User

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "full_name": "Admin User"
  }'
```

Response includes access token:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "admin@example.com",
    "full_name": "Admin User",
    "created_at": "2026-01-27T...",
    "is_active": true
  }
}
```

### 4. Create a Workspace

```bash
curl -X POST "http://localhost:8000/api/auth/workspaces" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "My Knowledge Base",
    "description": "Company knowledge graph"
  }'
```

### 5. Upload Documents

```bash
curl -X POST "http://localhost:8000/api/documents/upload?workspace_id=WORKSPACE_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

### 6. Query Your Knowledge Graph

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "query": "What is GraphRAG?",
    "workspace_id": "WORKSPACE_ID",
    "max_depth": 2,
    "top_k": 10
  }'
```

## 🔧 API Changes

### Breaking Changes

#### 1. **Authentication Required**
All API endpoints (except `/health` and registration/login) now require authentication:

```javascript
// Old way (no auth)
fetch('/api/query/', {
  method: 'POST',
  body: JSON.stringify({query: "..."})
})

// New way (with auth)
fetch('/api/query/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: "...",
    workspace_id: workspaceId
  })
})
```

#### 2. **Workspace ID Required**
Most operations now require a `workspace_id` parameter for data isolation.

#### 3. **New Endpoints**

**Authentication:**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `GET /api/auth/workspaces` - List workspaces
- `POST /api/auth/workspaces` - Create workspace

**Documents:**
- `POST /api/documents/upload` - Upload document
- `GET /api/documents/{document_id}/status` - Get processing status
- `GET /api/documents/` - List documents
- `DELETE /api/documents/{document_id}` - Delete document

**Schema Builder:**
- `GET /api/schema/{workspace_id}` - Get workspace schema
- `POST /api/schema/{workspace_id}/entity-types` - Create entity type
- `POST /api/schema/{workspace_id}/relationship-types` - Create relationship type
- `DELETE /api/schema/{workspace_id}/entity-types/{name}` - Delete entity type

**Export:**
- `POST /api/export/{workspace_id}` - Export graph data
- `GET /api/export/download/{export_id}/{filename}` - Download export

**Chatbot Widget:**
- `GET /api/chatbot/{workspace_id}/settings` - Get chatbot settings
- `PUT /api/chatbot/{workspace_id}/settings` - Update chatbot settings
- `POST /api/chatbot/chat` - Chat endpoint (API key auth)

## 🎨 Frontend Integration

### Using the Embeddable Chatbot

1. Get your API key from the workspace settings
2. Get the embed code from `/api/chatbot/{workspace_id}/settings`
3. Paste the code before `</body>` tag:

```html
<!-- GraphRAG Chatbot Widget -->
<script>
  (function() {
    var chatbotConfig = {
      workspaceId: 'your-workspace-id',
      apiKey: 'grag_xxxxxxxxxxxxxxxx',
      apiUrl: 'https://your-domain.com',
      title: 'AI Assistant',
      primaryColor: '#3B82F6',
      position: 'bottom-right'
    };
    var script = document.createElement('script');
    script.src = chatbotConfig.apiUrl + '/static/embed/chatbot.js';
    script.async = true;
    script.onload = function() {
      GraphRAGChatbot.init(chatbotConfig);
    };
    document.head.appendChild(script);
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = chatbotConfig.apiUrl + '/static/embed/chatbot.css';
    document.head.appendChild(link);
  })();
</script>
```

## 📊 Data Migration

### Migrating Existing Data

If you have existing data in the old format, you need to:

1. **Create a workspace** for existing data
2. **Add workspace relationships** to existing nodes:

```cypher
// Connect all existing nodes to a workspace
MATCH (w:Workspace {id: 'your-workspace-id'})
MATCH (n)
WHERE NOT (n:Workspace OR n:User OR n:APIKey OR n:Document)
CREATE (n)-[:IN_WORKSPACE]->(w)
```

3. **Update queries** to filter by workspace:

```cypher
// Old query
MATCH (n:Movie) RETURN n

// New query (workspace-filtered)
MATCH (n:Movie)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
RETURN n
```

## 🔒 Security Best Practices

### 1. Change JWT Secret
```env
# Generate a secure secret key
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Use HTTPS in Production
```python
# In production, update CORS to specific domains
allow_origins=["https://yourdomain.com"]
```

### 3. Set Strong Password Requirements
```python
# Already implemented: minimum 8 characters
# Consider adding: uppercase, lowercase, numbers, special chars
```

### 4. Enable Rate Limiting
```python
# Future implementation with Redis
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

## 🎯 Next Steps

### Immediate (Production Ready)
- [ ] Generate secure JWT secret key
- [ ] Configure production database credentials
- [ ] Set up Redis for background tasks
- [ ] Configure file upload limits
- [ ] Set up monitoring (Sentry, Prometheus)

### Short-term (Enhancement)
- [ ] Implement rate limiting
- [ ] Add email verification
- [ ] Add password reset functionality
- [ ] Create admin dashboard
- [ ] Add usage analytics

### Long-term (Scaling)
- [ ] Implement GraphQL API
- [ ] Add webhook support
- [ ] Create mobile apps
- [ ] Add real-time collaboration
- [ ] Implement vector database (Pinecone/Weaviate)

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Redis CLI**: `redis-cli`

## 🐛 Troubleshooting

### Issue: "Could not validate credentials"
**Solution**: Check if JWT token is expired or invalid. Login again to get new token.

### Issue: "No access to this workspace"
**Solution**: Verify you're using correct workspace_id and you have access rights.

### Issue: "File type not supported"
**Solution**: Check `allowed_extensions` in config. Supported: pdf, docx, txt, csv, json, xlsx, md, html

### Issue: Documents stuck in "processing" status
**Solution**: Check if Redis is running. Ensure background task worker is running.

## 🎉 Success!

You now have a production-ready multi-tenant GraphRAG SaaS platform!

For questions or issues, check the documentation or open an issue on GitHub.
