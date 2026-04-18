# Memory Leak Fix for Mid-Spec Laptops

## Problem
Document processing was consuming progressively more RAM (1GB → 2GB → 3GB → ...) until system crash. The issue occurred during background document ingestion after upload returned 200.

## Root Causes Identified

1. **Embedding Generation Loop**: Each chunk generated embeddings, and Ollama kept accumulating tensors in memory
2. **No Garbage Collection**: Variables weren't being deleted and GC wasn't forced between operations
3. **Too Large Batch Sizes**: Processing too many chunks at once without cleanup
4. **No Memory Monitoring**: No checks during processing to stop before system crash
5. **Aggressive Limits Missing**: Limits were too generous for mid-spec laptops without GPU

## Fixes Applied

### 1. GraphRAG Service ([app/services/graphrag_service.py](app/services/graphrag_service.py))

**Before:**
- Max content: 500KB
- Max chunks: 50
- Batch size: 5
- GC delay: 0.5s
- No memory monitoring during processing

**After:**
- Max content: **100KB** (ultra conservative)
- Max chunks: **20** (prevents progressive leak)
- Batch size: **3** (tiny batches)
- GC delay: **1.0s** (let system breathe)
- **Emergency stop at 80% memory** during processing
- **Force GC after each chunk** (not just batches)
- **Explicit variable deletion** (`del embedding`, `del chunk_properties`, etc.)
- **Finally block** ensures cleanup even on error

### 2. Configuration ([app/config.py](app/config.py))

```python
# OLD VALUES
chunk_size: 300
chunk_overlap: 30
chunk_batch_size: 5
max_parse_size_mb: 20
max_upload_size_mb: 20
memory_limit_percent: 75.0

# NEW VALUES (Optimized for mid-spec laptops)
chunk_size: 200              # Smaller chunks
chunk_overlap: 20            # Less overlap
chunk_batch_size: 3          # Tiny batches
max_parse_size_mb: 5         # Strict file size
max_upload_size_mb: 5        # Prevent large uploads
memory_limit_percent: 70.0   # Earlier rejection
memory_emergency_stop: 80.0  # NEW - emergency brake
```

### 3. Document Parser ([app/services/document_parser.py](app/services/document_parser.py))

**Drastically reduced limits:**
- PDF: 20 pages max (was 50), 5MB max (was 10MB), GC every 5 pages (was 10)
- DOCX: 200 paragraphs (was 500), 3MB max (was 5MB)
- CSV: 200 rows (was 500)
- Excel: 200 rows (was 500), 2 sheets (was 3)
- Page text: 5000 chars max (was 10000)

### 4. Document Upload Router ([app/routers/documents.py](app/routers/documents.py))

**Added comprehensive monitoring:**
```python
# Before parsing
gc.collect()

# After parsing
if memory.percent > 80%:
    abort()  # Emergency stop

# After ingestion
del text_content
gc.collect()

# In error handler
gc.collect()

# In finally block
gc.collect()  # Always cleanup
```

### 5. Ollama Service ([app/services/ollama_service.py](app/services/ollama_service.py))

**Embeddings optimization:**
- Truncate input to 2000 chars max
- Immediately delete response object
- Return embedding and let GC clean up

## Testing Recommendations

1. **Monitor memory during upload:**
   ```bash
   watch -n 1 free -h
   ```

2. **Test with different file sizes:**
   - Small file (100KB) - should work smoothly
   - Medium file (1MB) - should process with warnings
   - Large file (5MB+) - should reject at upload

3. **Check logs for memory reports:**
   ```bash
   tail -f logs/app.log | grep "Memory"
   ```

4. **Expected behavior:**
   - Upload returns 200 immediately
   - Background processing starts
   - Memory increases gradually
   - **Memory should stabilize** (not keep growing)
   - Processing completes or stops at 80% memory
   - Memory drops after completion

## Memory Thresholds

| Threshold | Action |
|-----------|--------|
| < 70% | ✅ Accept new uploads |
| 70-80% | ⚠️ Reject new uploads, continue existing |
| > 80% | 🛑 Emergency stop processing |

## What to Do If Still Crashing

If you still experience issues:

1. **Reduce limits even further** in [app/config.py](app/config.py):
   ```python
   chunk_size: 100
   max_chunks: 10  # In graphrag_service.py line 226
   batch_size: 2   # In graphrag_service.py line 242
   ```

2. **Use smaller files**: Start with <1MB files

3. **Check Ollama memory**: 
   ```bash
   docker stats  # If running Ollama in Docker
   ```

4. **Restart Ollama** between large uploads to clear model cache

5. **Consider disabling embeddings temporarily** for testing:
   - Comment out embedding generation in `graphrag_service.py`
   - This will break search but help isolate the issue

## Files Modified

- ✅ [app/services/graphrag_service.py](app/services/graphrag_service.py)
- ✅ [app/config.py](app/config.py)
- ✅ [app/services/document_parser.py](app/services/document_parser.py)
- ✅ [app/routers/documents.py](app/routers/documents.py)
- ✅ [app/services/ollama_service.py](app/services/ollama_service.py)

## Restart Required

After these changes, restart your application:

```bash
# Stop current server (Ctrl+C)
uvicorn app.main:app --reload
```

The server should now process documents without consuming all your RAM!
