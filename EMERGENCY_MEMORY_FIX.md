# Emergency Memory Leak Fix

## Problem
Even after disabling Ollama, document ingestion was still consuming all system resources (progressive leak: 1GB → 2GB → 3GB → crash). The uvicorn server had to be killed twice (Exit Code 137 = OOM kill).

## Root Causes Identified

### 1. **Excel Parser Loading ALL Sheets**
```python
# BEFORE (DANGEROUS):
excel_data = pd.read_excel(excel_file, sheet_name=None, nrows=max_rows)
# ☠️ sheet_name=None loads EVERY sheet into memory at once!
```

For a 155KB Excel file with multiple sheets, pandas was loading gigabytes into memory.

### 2. **Too Many Rows Being Processed**
- CSV: Was reading 200 rows → Now 50 rows max
- Excel: Was reading 200 rows → Now 50 rows max
- No memory checks before parsing

### 3. **Too Many Chunks**
- CSV/Excel: 50 chunks → Now 10 chunks max
- Text files: 20 chunks → Now 5 chunks max
- PDF/DOCX: 3 chunks → Now 2 chunks max

### 4. **Memory Threshold Too Late**
- Was checking at 60-70% → Now checks at 55-65%

## Fixes Applied

### 1. Excel Parser (CRITICAL FIX)
```python
# NOW (SAFE):
excel_data = pd.read_excel(excel_file, sheet_name=0, nrows=50, engine='openpyxl')
# ✅ Only reads FIRST sheet, max 50 rows

# Added memory check BEFORE parsing:
mem_before = psutil.virtual_memory().percent
if mem_before > 60:
    raise MemoryError("Memory too high - refusing to parse")
```

### 2. CSV Parser
```python
# Reduced from 200 to 50 rows
max_rows = min(max_rows, 50)

# Added memory monitoring before/after:
mem_before = psutil.virtual_memory().percent
if mem_before > 60:
    raise MemoryError("Memory too high")
    
# ... parse ...

mem_after = psutil.virtual_memory().percent
logger.info(f"Memory delta: +{mem_after-mem_before:.1f}%")
```

### 3. Chunk Limits (graphrag_service.py)
```python
# DRASTICALLY REDUCED:
if file_type in structured_types:
    max_chunks = 10  # Was 50
elif file_type in simple_types:
    max_chunks = 5   # Was 20
else:
    max_chunks = 2   # Was 3

# Emergency stop threshold:
if mem.percent > 65:  # Was 70%
    raise MemoryError("Emergency stop")
```

### 4. Document Upload Check (documents.py)
```python
# Check memory BEFORE starting processing:
if memory_percent > 55:  # Was 60%
    error_msg = "Memory too high - cannot process"
    # Update document status to failed
    return
```

### 5. Cell Value Truncation
```python
# Truncate individual cell values to 50 chars:
row_text = " | ".join([f"{col}: {str(val)[:50]}" for col, val in row.items()])
```

## Current Limits (Mid-Spec Laptop Mode)

| File Type | Max Rows | Max Chunks | Max Content | Embeddings |
|-----------|----------|------------|-------------|------------|
| Excel     | 50       | 10         | First sheet only | Never |
| CSV       | 50       | 10         | 50KB       | Never |
| Text/MD   | N/A      | 5          | 50KB       | Never |
| PDF       | 20 pages | 2          | 5-20KB     | Optional |
| DOCX      | 200 para | 2          | 5-20KB     | Optional |

## Memory Thresholds

| Stage | Threshold | Action |
|-------|-----------|--------|
| Upload start | 55% | Reject document |
| Parser start | 60% | Refuse to parse |
| During chunks | 65% | Emergency stop |
| Parser memory | 60-70% | Refuse parsing |

## Testing Required

1. **Excel File (155KB)**
   - Should only read first sheet
   - Should process max 10 chunks (not 50)
   - Should complete without memory leak

2. **CSV File**
   - Max 50 rows, 10 chunks
   - Should log memory delta

3. **Text File**
   - Max 5 chunks only

## How to Test

```bash
# 1. Clear any stuck processes
lsof -ti:8000 | xargs kill -9 2>/dev/null || pkill -9 uvicorn

# 2. Start fresh server
source venv/bin/activate
uvicorn app.main:app --reload

# 3. Monitor memory during upload
watch -n 1 'free -h && ps aux | grep uvicorn | grep -v grep'

# 4. Upload Excel file and watch logs:
# Should see:
# - "Excel parsing started - Memory: XX%"
# - "Sheet: First Sheet Only (memory safety)"
# - "Rows: 50 (limited to 50)"
# - "EMERGENCY: Limiting chunks from X to 10"
# - "Excel parsing complete - Memory: YY% (delta: +Z%)"
```

## Expected Behavior

1. **Before parsing**: Memory check refuses if >60%
2. **During parsing**: Only first Excel sheet loaded
3. **After parsing**: Memory delta logged
4. **Chunk processing**: Max 10 chunks for Excel/CSV
5. **Emergency stop**: Triggers at 65% memory

## If Still Crashing

If memory issues persist, further reduce limits:

```python
# In document_parser.py:
max_rows = min(max_rows, 25)  # Reduce to 25 rows

# In graphrag_service.py:
max_chunks = 5  # For all file types

# In documents.py:
if memory_percent > 50:  # Even more aggressive
```

## Key Insight

**The problem wasn't just Ollama** - pandas was loading entire Excel workbooks into memory. Even without embeddings, large DataFrames consume massive RAM on iterrows() operations.

**Solution**: Only read what's absolutely necessary (first sheet, limited rows), check memory before every operation, truncate aggressively.
