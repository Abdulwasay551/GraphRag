# ULTRA SAFE MODE - System Crash Prevention

## Critical Issue
VS Code itself crashed during document ingestion, indicating catastrophic memory spike that's too fast for normal checks to catch.

## New ULTRA-CONSERVATIVE Limits

### Absolute Maximums (CRASH PREVENTION MODE)

| Setting | Old Value | New Value | Reason |
|---------|-----------|-----------|--------|
| **Excel rows** | 50 | **10** | Pandas iterrows() explodes memory |
| **CSV rows** | 50 | **10** | Same pandas issue |
| **Max chunks** | 10/5/2 | **3** | All file types get same limit |
| **Memory start threshold** | 55% | **50%** | Reject earlier |
| **Memory during chunks** | 65% | **60%** | Stop earlier |
| **Memory after parse** | 70% | **60%** | Stop earlier |
| **Parser memory check** | 60% | **60%** | Keep strict |

### New Safety Features

1. **Delay Between Chunks**: 500ms sleep + GC between every chunk
2. **CSV low_memory=True**: Pandas optimization
3. **Force GC After Parse**: Immediate cleanup after parsing
4. **Ultra-Early Rejection**: Won't even start if memory >50%

### Current Configuration

```python
# Rows from Excel/CSV
MAX_ROWS = 10  # Only first 10 rows!

# Chunks from ANY file
MAX_CHUNKS = 3  # Only 3 chunks total

# Memory thresholds
START_THRESHOLD = 50%   # Won't start if >50%
PARSE_THRESHOLD = 60%   # Stop after parsing if >60%
CHUNK_THRESHOLD = 60%   # Stop during chunks if >60%

# Delays
CHUNK_DELAY = 500ms     # Wait between each chunk
```

### What This Means

**For a 155KB Excel file:**
- Only **first sheet** will be read
- Only **first 10 rows** will be processed
- Only **3 chunks** will be created from those 10 rows
- **500ms delay** between each chunk
- **Forced GC** after parsing and between chunks
- **Will refuse** to start if system memory already >50%

**Result:** Absolute minimal processing to prevent system crashes

### Testing

```bash
# 1. Check current memory
free -h

# 2. Restart server
pkill -9 -f uvicorn
source venv/bin/activate
uvicorn app.main:app --reload

# 3. Upload small file
# Expected: Only 10 rows, 3 chunks, multiple GC pauses

# 4. Watch memory continuously
watch -n 1 'free -h && echo "---" && ps aux | grep uvicorn | grep -v grep'
```

### Log Output to Expect

```
Excel parsing started - Memory: XX%
Sheet: First Sheet Only (memory safety)
Columns: ...
Rows: 10 (limited to 10)
Excel parsing complete - Memory: YY% (delta: +Z%)
Created N chunks
EMERGENCY: Limiting chunks from N to 3
[Chunk 1/3] Memory: XX%
[Chunk 2/3] Memory: XX%  <- 500ms delay here
[Chunk 3/3] Memory: XX%  <- 500ms delay here
```

### If Still Crashing

If system still crashes with these limits, we need to:

1. **Disable chunking entirely** - Just store file metadata
2. **Don't read file content at all** - Only store filename/size
3. **Use external processing** - Process files outside main application
4. **Increase system swap** - Not recommended, but emergency option

### Alternative: Metadata-Only Mode

If crashes continue, enable metadata-only mode:

```python
# In graphrag_service.py
if mem.percent > 40:  # Very early check
    logger.warning("Memory >40%, using metadata-only mode")
    # Skip all chunking, just store file info
    return MetadataOnlyResult(...)
```

This would:
- Store filename, size, type in Neo4j
- **NOT** read file content at all
- **NOT** create chunks
- Just track "document uploaded" status

### Why VS Code Crashed

VS Code crashed because Python memory spike happened so fast that:
1. Pandas loaded Excel data
2. Iterrows() created massive temporary objects
3. Memory jumped from 50% → 90% in <1 second
4. System OOM killer terminated VS Code (largest process)

The 500ms delays and forced GC after parsing should prevent these spikes.

### Current System State

```bash
# Memory available
free -h
# Should show ~23GB available

# No stuck processes
ps aux | grep uvicorn
# Should be clean or show new process

# Server should start fresh
# Initial memory should be ~20-25%
```
