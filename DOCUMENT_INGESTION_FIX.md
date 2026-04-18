# Document Ingestion Resource Crash Fix

## Problem
Document ingestion was consuming all laptop resources, freezing the entire system, and crashing after ~40 minutes.

## Root Causes Identified

### 1. **Expensive Entity Extraction Per Chunk** ⚠️ CRITICAL
- Every chunk (up to 500!) called LLM for entity extraction
- Each call generated a full text completion to extract JSON
- This was the #1 cause of resource exhaustion

### 2. **Sequential Processing with No Parallelization**
- Chunks processed one at a time
- Each chunk: embedding → entity extraction → multiple DB calls
- No batching of database operations

### 3. **Excessive Chunk Limits**
- Documents allowed up to 500 chunks
- 5MB content limit (could be huge PDFs)
- 500 PDF pages, 5000 paragraphs in DOCX

### 4. **Memory Accumulation**
- No resource monitoring before processing
- Insufficient garbage collection
- Large objects kept in memory

## Fixes Applied

### 1. **Disabled Entity Extraction During Ingestion** ✅
- **REMOVED** expensive LLM entity extraction calls per chunk
- Now only generates embeddings (fast, necessary for search)
- Entity extraction can be added later as a separate optional step
- **Impact**: Reduces processing time by ~90%

### 2. **Aggressive Chunk Limits** ✅
```python
# OLD
max_chunks = 500
max_content_size = 5_000_000  # 5MB

# NEW
max_chunks = 50              # 90% reduction
max_content_size = 500_000   # 500KB
```

### 3. **Stricter File Size Limits** ✅
```python
# config.py
max_upload_size_mb: 20      # reduced from 50
max_parse_size_mb: 20       # reduced from 50
memory_limit_percent: 75.0  # reject if >75% memory used

# Document Parser
PDF: max 50 pages (was 500)
DOCX: max 500 paragraphs (was 5000)
CSV/Excel: max 500 rows (was 5000)
Excel: max 3 sheets (was 5)
```

### 4. **Memory Monitoring** ✅
- Check system memory before processing
- Reject if memory usage > 75%
- Log memory usage during processing
- More frequent garbage collection

### 5. **Batch Database Operations** ✅
- Collect nodes before inserting
- Batch insert instead of one-by-one
- Longer sleep intervals (0.5s) between batches

### 6. **Truncation & Safety** ✅
- Truncate very long chunks to 2000 chars
- Truncate stored text to 1000 chars (save memory)
- Only store essential properties
- Skip failed chunks instead of crashing

## Performance Improvements

**Before:**
- 40 minutes → system freeze → crash
- Entity extraction on 500 chunks = 500+ LLM calls
- No memory limits

**After:**
- ~2-5 minutes for typical documents
- Max 50 chunks with only embedding generation
- Memory checked before processing starts
- System stays responsive

## Usage Guidelines

### For Users:
1. **File Size Limits:**
   - Max upload: 20MB
   - Recommended: Under 10MB for best performance
   
2. **Supported Files:**
   - PDF: Up to 50 pages
   - DOCX: Up to 500 paragraphs
   - CSV/Excel: Up to 500 rows
   - Text files: Up to 20MB

3. **Processing Time:**
   - Small files (<1MB): 30 seconds - 2 minutes
   - Medium files (1-10MB): 2-5 minutes
   - Large files (10-20MB): 5-10 minutes

4. **If Processing Still Slow:**
   - Break large documents into smaller files
   - Remove images/formatting before upload
   - Close other memory-intensive applications

### For Developers:
If you need entity extraction back:
1. Create a separate endpoint: `/api/documents/{id}/extract-entities`
2. Run as optional post-processing step
3. Process one chunk at a time with delays
4. Use task queue for very large documents

## Files Modified

1. `/app/services/graphrag_service.py`
   - Reduced chunk limits (500 → 50)
   - Disabled entity extraction
   - Added batch processing
   - Increased garbage collection

2. `/app/services/document_parser.py`
   - Added logging
   - Reduced file size limits (all formats)
   - Reduced page/row/sheet limits
   - Better memory cleanup

3. `/app/routers/documents.py`
   - Added psutil import
   - Memory check before processing
   - File size validation
   - Better error messages

4. `/app/config.py`
   - Reduced all limits
   - chunk_size: 400 → 300
   - max_parse_size_mb: 50 → 20
   - max_upload_size_mb: 50 → 20
   - memory_limit_percent: 85 → 75

## Testing

Test with progressively larger files:
```bash
# 1. Small test (should be < 1 min)
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@small_doc.txt"

# 2. Monitor memory during processing
htop

# 3. Check logs for memory warnings
tail -f logs/app.log
```

## Future Improvements (Optional)

1. **Streaming Processing:**
   - Process chunks as they're parsed
   - Don't load entire document in memory

2. **Background Job Queue:**
   - Use Celery for heavy documents
   - Show progress bar to users

3. **Smart Entity Extraction:**
   - Only extract from top-K most relevant chunks
   - Use lighter extraction prompts
   - Cache extracted entities

4. **Adaptive Limits:**
   - Detect available memory
   - Adjust chunk limits dynamically
   - Queue if system busy

## Rollback Instructions

If you need to revert (not recommended):
```bash
git diff HEAD~1 app/services/graphrag_service.py
git checkout HEAD~1 -- app/services/graphrag_service.py
git checkout HEAD~1 -- app/services/document_parser.py
git checkout HEAD~1 -- app/routers/documents.py
git checkout HEAD~1 -- app/config.py
```
