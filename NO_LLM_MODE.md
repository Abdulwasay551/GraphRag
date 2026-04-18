# No-LLM Mode - Smart File Type Processing

## How It Works Now

Your system uses **SMART FILE TYPE DETECTION** to avoid Ollama/LLM when not needed:

### File Type Handling

| File Type | Ollama/LLM Used? | Why |
|-----------|-----------------|-----|
| **CSV** | ❌ NEVER | Already structured data |
| **Excel (XLSX/XLS)** | ❌ NEVER | Already structured data |
| **JSON** | ❌ NEVER | Already structured data |
| **TXT** | ❌ NO (default) | Simple text storage |
| **Markdown (MD)** | ❌ NO (default) | Simple text storage |
| **PDF** | ⚙️ Optional | Can enable if needed |
| **DOCX** | ⚙️ Optional | Can enable if needed |

## Current Configuration

```python
# In app/config.py
enable_embeddings: False  # Safe - no system crash

# What this means:
# - CSV/Excel: ALWAYS direct parsing, NEVER uses Ollama
# - TXT/MD/JSON: Simple storage, no Ollama
# - PDF/DOCX: No Ollama unless you enable it
```

## What You Can Do Now

### ✅ Upload CSV Files (SAFE)
- Direct parsing, no LLM
- Rows limited to 100 (configurable)
- Memory safe
- **No system crash risk**

### ✅ Upload Text Files (SAFE)  
- Store as chunks
- Keyword search works
- No embeddings needed
- **No system crash risk**

### ✅ Upload Excel Files (SAFE)
- Direct parsing, no LLM
- 2 sheets max, 100 rows max
- Memory safe
- **No system crash risk**

### ✅ Upload JSON (SAFE)
- Direct parsing
- Stored as chunks
- **No system crash risk**

### ⚠️ Upload PDF/DOCX (Safe in current mode)
- Currently NO embeddings (safe)
- Can enable later if you want

## Enabling LLM for PDFs (Optional - After Testing)

If you want to try embeddings for PDF/DOCX after confirming system stability:

1. **Test with small files first** (<100KB)
2. **Enable in config**:
   ```python
   enable_embeddings: True  # In app/config.py
   ```
3. **Monitor memory**: `watch -n 1 free -h`
4. **Start with ONE small PDF**
5. **If system crashes, immediately disable**

## Processing Flow

### CSV/Excel Example:
```
Upload CSV → Parse directly → Split into chunks → Store in Neo4j
(No Ollama, no LLM, no embeddings)
```

### Text File Example:
```
Upload TXT → Read text → Split into chunks → Store in Neo4j
(No Ollama, no LLM, no embeddings)
```

### PDF Example (embeddings disabled):
```
Upload PDF → Extract text → Split into chunks → Store in Neo4j
(No Ollama unless enabled)
```

## Limits (Conservative for Safety)

- Max upload: 2MB
- Max content: 5KB processed
- Max chunks: 3 per document
- Memory stop: 70%
- CSV rows: 100 max
- Excel rows: 100 max, 2 sheets

## Search Capabilities

- ✅ **Keyword search**: Works for all files
- ❌ **Semantic search**: Disabled (needs embeddings)
- ✅ **Graph relationships**: Works
- ❌ **LLM answers**: Disabled (shows found text instead)

## Benefits of This Approach

1. **No System Crashes** - Ollama only used when necessary
2. **CSV Works Perfectly** - Already structured, no LLM needed
3. **Fast Processing** - No waiting for embeddings
4. **Memory Safe** - No progressive memory leak
5. **Flexible** - Can enable LLM later for specific file types

## Testing Recommendations

1. **Start with CSV** - Upload a small CSV file first
2. **Try TXT files** - Simple and safe
3. **Monitor memory**: `watch -n 1 free -h`
4. **Check logs** for "Embeddings: DISABLED" confirmations

## Server Started?

Run:
```bash
cd /home/bnb/Documents/GraphRAG
source venv/bin/activate
uvicorn app.main:app --reload
```

Then upload `test_small.txt` or any CSV file - should work without crashing!
