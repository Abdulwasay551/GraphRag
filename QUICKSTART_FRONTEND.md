# Quick Start Guide - GraphRAG Frontend 🚀

## Prerequisites
- Python 3.8+
- Neo4j database running
- Ollama with llama3.2:1b model

## Setup Steps

### 1. Install Dependencies
```bash
cd /home/bnb/Documents/GraphRAG
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` file in project root:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama Configuration
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# Authentication (generate secure keys in production)
SECRET_KEY=your-secret-key-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis (optional for background tasks)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Initialize Database
```bash
python scripts/init_db.py
```

### 4. Start the Application
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access the Application
Open your browser and navigate to:
- **Landing Page**: http://localhost:8000
- **Login**: http://localhost:8000/login
- **Register**: http://localhost:8000/register
- **API Docs**: http://localhost:8000/docs

## First-Time Setup Flow

### Step 1: Create Account
1. Go to http://localhost:8000
2. Click "Start Free" or navigate to `/register`
3. Fill in:
   - Full Name
   - Email
   - Password (min 8 characters)
4. Accept Terms of Service
5. Click "Create Account"

### Step 2: Login
1. Navigate to `/login`
2. Enter your email and password
3. Click "Sign In"
4. You'll be redirected to `/dashboard`

### Step 3: Create Workspace
1. On dashboard, click "New Workspace"
2. Enter workspace name (e.g., "My Knowledge Graph")
3. Add optional description
4. Click "Create"

### Step 4: Upload Documents
1. Click on a workspace card
2. Click "Upload" button
3. Drag files or click "Select Files"
4. Supported formats:
   - PDF documents
   - Word files (.docx)
   - CSV spreadsheets
   - Excel files (.xlsx)
   - JSON data
   - Markdown (.md)
   - HTML files
5. Click "Upload All"
6. Wait for processing to complete

### Step 5: Explore Your Graph
1. Return to workspace detail page
2. View the interactive graph visualization
3. See entity types in the sidebar
4. Check recently uploaded documents

### Step 6: Query Your Data
1. Click "Query Graph" in quick actions
2. Ask natural language questions like:
   - "What entities exist in my graph?"
   - "Show me recent relationships"
   - "Summarize my documents"
3. View AI-generated responses with entity references

## Features Overview

### 🎨 Dark Mode
- Toggle with moon/sun icon in navbar
- Preference saved in browser
- Smooth theme transitions

### 📊 Dashboard
- View all workspaces
- See aggregate stats (nodes, documents, relationships)
- Quick access to recent activity
- Create new workspaces

### 📁 Document Upload
- Drag-and-drop interface
- Multi-file upload
- Real-time progress tracking
- AI-powered entity extraction

### 🔍 Query Interface
- Natural language queries
- Conversational AI responses
- Entity references in answers
- Chat history maintained

### 📈 Graph Visualization
- Interactive force-directed graph
- Zoom controls (in, out, reset)
- Node dragging
- Hover tooltips
- Based on D3.js

### 🎯 Workspace Management
- Multiple isolated workspaces
- Custom names and descriptions
- Plan-based resource limits:
  - Free: 1 workspace, 1K nodes
  - Pro: 10 workspaces, 50K nodes
  - Enterprise: Unlimited

## API Endpoints

### Authentication
```bash
# Register
POST /api/auth/register
Body: {"username": "John", "email": "john@example.com", "password": "secret123"}

# Login
POST /api/auth/login
Body: {"username": "john@example.com", "password": "secret123"}
Returns: {"access_token": "...", "token_type": "bearer"}

# List Workspaces
GET /api/auth/workspaces
Headers: {"Authorization": "Bearer <token>"}

# Create Workspace
POST /api/auth/workspaces
Headers: {"Authorization": "Bearer <token>"}
Body: {"name": "My Workspace", "description": "Optional"}
```

### Document Management
```bash
# Upload Document
POST /api/documents/upload?workspace_id=<id>
Headers: {"Authorization": "Bearer <token>"}
Body: FormData with file

# List Documents
GET /api/documents/list?workspace_id=<id>
Headers: {"Authorization": "Bearer <token>"}

# Get Document Status
GET /api/documents/status/<document_id>
Headers: {"Authorization": "Bearer <token>"}
```

### Query
```bash
# Natural Language Query
POST /api/query
Headers: {"Authorization": "Bearer <token>"}
Body: {"query": "What entities exist?", "workspace_id": "<id>"}
```

### Visualization
```bash
# Get Graph Data
GET /api/visualization/graph?workspace_id=<id>&limit=50
Headers: {"Authorization": "Bearer <token>"}

# Get Stats
GET /api/visualization/stats?workspace_id=<id>
Headers: {"Authorization": "Bearer <token>"}
```

## Testing

### Manual Testing
```bash
# Test landing page
curl http://localhost:8000

# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"test1234"}'

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test1234"

# Test protected endpoint
curl -X GET http://localhost:8000/api/auth/workspaces \
  -H "Authorization: Bearer <your_token>"
```

### Browser Testing
1. Open DevTools (F12)
2. Check Console for errors
3. Verify localStorage contains:
   - `darkMode` (true/false)
   - `access_token` (after login)
   - `user_data` (after login)
4. Test responsive design:
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)

## Troubleshooting

### Issue: Templates Not Loading
**Error**: `TemplateNotFound: landing.html`

**Solution**:
```bash
# Verify template files exist
ls app/templates/
# Should show: base.html, landing.html, login.html, etc.

# Restart server
uvicorn app.main:app --reload
```

### Issue: Dark Mode Not Working
**Symptom**: Toggle doesn't switch themes

**Solution**:
1. Clear browser localStorage
2. Hard refresh (Ctrl+Shift+R)
3. Check browser console for JavaScript errors

### Issue: API Calls Failing (401 Unauthorized)
**Symptom**: Redirected to login after making requests

**Solution**:
1. Check if token exists: `localStorage.getItem('access_token')`
2. Token may have expired (24h default)
3. Login again to get fresh token

### Issue: Upload Not Working
**Symptom**: Files don't upload or show errors

**Solution**:
1. Check file size (max 50MB)
2. Verify file format is supported
3. Check backend logs for parsing errors
4. Ensure workspace_id is valid

### Issue: Graph Not Rendering
**Symptom**: Empty white box where graph should be

**Solution**:
1. Verify D3.js loaded: Check Network tab for `d3.v7.min.js`
2. Check console for JavaScript errors
3. Ensure workspace has nodes: Upload documents first
4. Try different browser (Chrome/Firefox)

### Issue: Styling Looks Wrong
**Symptom**: Plain HTML without styles

**Solution**:
1. Check Tailwind CDN loaded: Look for `cdn.tailwindcss.com` in Network tab
2. Clear browser cache
3. Verify no ad blocker blocking CDN resources
4. Check browser console for blocked content

## Performance Tips

### Development
- Use `--reload` flag for auto-restart on code changes
- Keep DevTools open to monitor network requests
- Use browser's responsive design mode for mobile testing

### Production
- Use multiple workers: `--workers 4`
- Enable gzip compression
- Serve static files with CDN
- Use production database with proper indexing
- Set up Redis for caching

## Security Notes

### Development Mode
- Default secret key is insecure
- CORS allows all origins
- Debug mode enabled

### Production Checklist
- [ ] Generate secure SECRET_KEY (32+ characters)
- [ ] Disable debug mode
- [ ] Configure CORS for specific domains
- [ ] Use HTTPS/TLS certificates
- [ ] Set secure cookie flags
- [ ] Implement rate limiting
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor logs for suspicious activity

## Browser Support

### Fully Supported
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Partially Supported
- ⚠️ Safari 13 (some CSS features may not work)
- ⚠️ Firefox 85-87 (backdrop-filter requires flag)

### Not Supported
- ❌ Internet Explorer (use Edge instead)
- ❌ Chrome < 80
- ❌ Firefox < 80

## Keyboard Shortcuts

### Global
- `Ctrl/Cmd + K`: Focus search (when implemented)
- `Esc`: Close modals/dropdowns

### Chat Interface
- `Enter`: Send message
- `Shift + Enter`: New line in message

### Graph Visualization
- `Scroll`: Zoom in/out
- `Click + Drag`: Pan view
- `Click Node`: Select/highlight

## Mobile Experience

### Optimizations Applied
- Touch-friendly button sizes (min 44x44px)
- Responsive grid layouts
- Collapsible mobile menu
- Swipe gestures (native browser)
- Reduced animation on mobile

### Known Limitations
- Graph visualization less performant on mobile
- Drag-drop may require file picker on iOS
- Some hover effects don't work (use tap instead)

## Next Features to Implement

### High Priority
1. Schema builder UI
2. Chatbot embed settings
3. Export functionality UI
4. User settings page
5. Team management

### Medium Priority
1. Search functionality
2. Filters and sorting
3. Bulk operations
4. Activity history
5. Notifications panel

### Low Priority
1. PWA support
2. Offline mode
3. Keyboard shortcuts panel
4. Tour/onboarding
5. Print styles

---

**Need Help?** Check the API docs at `/docs` or review error logs in the terminal where you started the server.

**Ready to Deploy?** See `DEPLOYMENT.md` (create this next) for production setup instructions.
