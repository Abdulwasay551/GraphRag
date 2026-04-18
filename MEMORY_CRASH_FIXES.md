# Memory Crash Fixes - Complete Guide

## Critical Memory Optimizations Applied

Your GraphRAG application has been equipped with **aggressive memory management** to prevent crashes and RAM exhaustion.

## Changes Made

### 1. **GraphRAG Service** (`app/services/graphrag_service.py`)
- ✅ Added forced garbage collection before/after every query
- ✅ Limited query input to 10,000 characters
- ✅ Reduced max_depth to 2, top_k to 20 (hard limits)
- ✅ Reduced response size (15 nodes max, 30 relationships max)
- ✅ Removed large property values from responses (truncated to 500 chars)
- ✅ Added memory cleanup between operations
- ✅ Limited document content to 5MB per file
- ✅ Limited chunks to 500 per document
- ✅ Reduced batch size to 2-3 chunks at a time
- ✅ Added garbage collection after each batch
- ✅ Added 0.1s delay between batches to let system breathe

### 2. **Document Parser** (`app/services/document_parser.py`)
- ✅ Added file size limits (50MB per file)
- ✅ Limited PDF parsing to 500 pages with GC every 50 pages
- ✅ Limited DOCX parsing to 5,000 paragraphs
- ✅ Limited CSV/Excel to 5,000 rows and 5 sheets max
- ✅ Added explicit memory cleanup after each file parse
- ✅ Forced garbage collection after document parsing

### 3. **Neo4j Service** (`app/services/neo4j_service.py`)
- ✅ Limited connection pool to 10 connections max
- ✅ Added 30-second connection timeout
- ✅ Limited fetch size to 100 records
- ✅ Limited query results to 1,000 records max with auto-truncation
- ✅ Limited semantic search to 50 results max
- ✅ Limited neighbor expansion depth to 2 max

### 4. **Memory Monitor Middleware** (`app/middleware/memory_monitor.py`) ⭐ NEW
- ✅ Monitors memory usage on every request
- ✅ Logs memory stats every 10 requests
- ✅ Forces triple garbage collection when memory > 85%
- ✅ Rejects requests with 503 if memory still high after GC
- ✅ Periodic GC every 50 requests
- ✅ Pre-operation memory checks for expensive operations

### 5. **Configuration** (`app/config.py`)
- ✅ Reduced chunk_size: 500 → 400
- ✅ Reduced chunk_overlap: 50 → 40
- ✅ Reduced chunk_batch_size: 5 → 2
- ✅ Reduced max_csv_rows: 10,000 → 5,000
- ✅ Reduced max_parse_size_mb: 100 → 50
- ✅ Added memory_limit_percent: 85%

### 6. **Chatbot Router** (`app/routers/chatbot.py`)
- ✅ Limited query input to 2,000 characters
- ✅ Limited depth to 2, top_k to 15
- ✅ Truncated answers to 5,000 characters
- ✅ Limited sources to 5 max

### 7. **Health Monitoring** (`app/routers/health.py`) ⭐ NEW
- ✅ GET `/api/health/` - Real-time memory and system stats
- ✅ POST `/api/health/gc` - Force garbage collection endpoint

## How to Use

### Monitor Memory in Real-Time
```bash
# Check memory stats
curl http://localhost:8000/api/health/

# Sample response:
{
  "status": "healthy",
  "neo4j": true,
  "memory": {
    "percent": 42.5,
    "used_gb": 12.75,
    "total_gb": 30.0,
    "available_gb": 17.25,
    "status": "ok"
  },
  "swap": {
    "percent": 15.2,
    "used_gb": 1.22,
    "total_gb": 8.0
  }
}
```

### Force Garbage Collection Manually
```bash
# If memory is high, force cleanup
curl -X POST http://localhost:8000/api/health/gc

# Sample response:
{
  "status": "completed",
  "before": {
    "memory_percent": 78.5,
    "memory_used_gb": 23.55
  },
  "after": {
    "memory_percent": 65.2,
    "memory_used_gb": 19.56
  },
  "freed_mb": 4086.4
}
```

### Restart the Server
```bash
# Stop the current server (Ctrl+C)
# Then restart with:
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Memory-Safe Usage Guidelines

### ✅ DO:
1. **Keep documents under 50MB**
2. **Process files in batches** - upload 2-3 at a time, not 50
3. **Monitor memory** regularly via `/api/health/`
4. **Use smaller chunk sizes** for large documents
5. **Limit graph depth to 1-2** in queries
6. **Close browser tabs** when not using the UI

### ❌ DON'T:
1. **Upload massive PDFs** (>100 pages)
2. **Upload huge Excel files** (>10,000 rows)
3. **Query with depth > 2**
4. **Fetch >20 results per query**
5. **Run multiple heavy operations simultaneously**
6. **Keep server running for days without restart**

## Memory Status Indicators

The system will automatically:
- **Log warnings** when memory exceeds 80%
- **Force garbage collection** at 85%
- **Reject requests with 503** if memory stays above 85%
- **Auto-truncate** large responses
- **Clean up after every operation**

## Troubleshooting

### If Crashes Still Occur:

1. **Reduce limits further** in `app/config.py`:
   ```python
   chunk_batch_size: int = 1  # Process 1 chunk at a time
   max_csv_rows: int = 1000   # Even smaller files
   max_parse_size_mb: int = 20  # Smaller file size
   memory_limit_percent: float = 75.0  # More aggressive threshold
   ```

2. **Increase system memory**:
   - Add swap space: `sudo fallocate -l 8G /swapfile`
   - Close other applications
   - Restart services

3. **Use external processing**:
   - Pre-process large documents outside the app
   - Split large files into smaller chunks
   - Use command-line tools for initial parsing

4. **Monitor with system tools**:
   ```bash
   # Watch memory in real-time
   watch -n 2 free -h
   
   # Check Python process memory
   ps aux | grep python | grep -v grep
   
   # Monitor with htop
   htop
   ```

5. **Set Python memory limit** (optional):
   ```bash
   # Limit Python to 20GB
   ulimit -v 20971520
   uvicorn app.main:app --reload
   ```

## Performance Tuning

### For Low-Memory Systems (<16GB):
```python
# In app/config.py
chunk_batch_size: int = 1
max_csv_rows: int = 1000
max_parse_size_mb: int = 20
memory_limit_percent: float = 70.0
```

### For Medium Systems (16-32GB):
```python
# Current settings (default)
chunk_batch_size: int = 2
max_csv_rows: int = 5000
max_parse_size_mb: int = 50
memory_limit_percent: float = 85.0
```

### For High-Memory Systems (>32GB):
```python
# Can increase slightly
chunk_batch_size: int = 5
max_csv_rows: int = 10000
max_parse_size_mb: int = 100
memory_limit_percent: float = 90.0
```

## What Was Fixed

### Before:
- ❌ No memory monitoring
- ❌ No garbage collection
- ❌ Unlimited file sizes
- ❌ No connection pooling limits
- ❌ Large responses consuming memory
- ❌ No request throttling based on memory

### After:
- ✅ Real-time memory monitoring
- ✅ Aggressive garbage collection
- ✅ Strict file size limits
- ✅ Connection pool limits (10 max)
- ✅ Reduced response sizes
- ✅ Automatic request rejection when memory high
- ✅ Health endpoints for monitoring
- ✅ Memory stats logging
- ✅ Batch processing with delays

## Testing the Fixes

1. **Start fresh**:
   ```bash
   source venv/bin/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Monitor in terminal 1**:
   ```bash
   watch -n 2 'curl -s http://localhost:8000/api/health/ | jq .memory'
   ```

3. **Test in terminal 2**:
   ```bash
   # Upload a document
   # Run queries
   # Watch memory stay stable
   ```

The system should now be **significantly more stable** and **won't consume all your RAM**. 

If you still experience crashes, the issue may be:
1. System-level (Pylance using 545MB - can be disabled)
2. Need to restart the server more frequently
3. Need to reduce limits even further
4. Hardware limitations (upgrade RAM or add swap)
