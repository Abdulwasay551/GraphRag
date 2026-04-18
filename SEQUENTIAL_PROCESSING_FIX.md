# Emergency Fix: Sequential Processing for Low-Spec Laptops

## Critical Changes Applied

### Problem Root Cause
- **Ollama was being bombarded** with multiple embedding requests simultaneously
- Memory accumulated progressively as embeddings piled up
- System couldn't keep up with garbage collection

### Solution: STRICT Sequential Processing

Now processing **ONE chunk at a time** with 2-second delays between each chunk.

## New Limits (EXTREME MODE)

```python
# Content limits
max_content_size: 30KB (was 100KB)
max_chunks: 10 (was 20)
max_upload_size: 2MB (was 5MB)

# Processing
batch_size: 1 (strictly sequential)
delay_between_chunks: 2 seconds
memory_emergency_stop: 75% (was 80%)

# Chunking
chunk_size: 150 chars (was 200)
chunk_overlap: 10 chars (was 20)
```

## How It Works Now

**Before (BULK):**
```
[Chunk 1] → Ollama
[Chunk 2] → Ollama  ← All at once, memory explodes
[Chunk 3] → Ollama
[Chunk 4] → Ollama
```

**After (SEQUENTIAL):**
```
[Chunk 1] → Ollama → Wait 2s → Cleanup → ✓
[Chunk 2] → Ollama → Wait 2s → Cleanup → ✓
[Chunk 3] → Ollama → Wait 2s → Cleanup → ✓
[Chunk 4] → Ollama → Wait 2s → Cleanup → ✓
```

## Processing Flow

1. **Upload** → Returns 200 immediately
2. **Parse** → Truncates to 30KB max
3. **Chunk** → Creates max 10 chunks
4. **For each chunk sequentially:**
   - Check memory (abort if >75%)
   - Generate embedding (ONE request to Ollama)
   - Update progress in database
   - Store in Neo4j
   - Delete all variables
   - Force garbage collection
   - **Sleep 2 seconds** (let system recover)
   - Log: `[Chunk X/10] ✓ Complete`

## Live Progress Updates

### Backend
Progress is now stored in the database:
- `progress` - percentage (0-100)
- `progress_message` - e.g., "Processing chunk 3 of 10"
- `chunks_processed` - number completed

### Frontend - Add to upload.html

```javascript
// After upload succeeds
async function pollDocumentStatus(documentId, workspaceId) {
    const statusDiv = document.getElementById('upload-status');
    
    const poll = async () => {
        try {
            const response = await fetch(
                `/api/documents/${documentId}/status?workspace_id=${workspaceId}`,
                {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                }
            );
            
            const data = await response.json();
            
            // Update UI
            statusDiv.innerHTML = `
                <div class="progress-container">
                    <div class="progress-bar" style="width: ${data.progress}%"></div>
                </div>
                <p>${data.progress_message || data.status}</p>
                <p>Chunks processed: ${data.chunks_processed}</p>
            `;
            
            // Continue polling if still processing
            if (data.status === 'processing') {
                setTimeout(poll, 2000); // Poll every 2 seconds
            } else if (data.status === 'completed') {
                statusDiv.innerHTML = '<p class="success">✓ Document processed successfully!</p>';
            } else if (data.status === 'failed') {
                statusDiv.innerHTML = `<p class="error">✗ Failed: ${data.error_message}</p>`;
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    };
    
    poll(); // Start polling
}

// In your upload handler:
const result = await uploadResponse.json();
pollDocumentStatus(result.document_id, workspaceId);
```

## Expected Behavior

### Console Logs (Sequential):
```
[Chunk 1/10] Memory: 25.3%
[Chunk 1/10] Generating embedding...
[Chunk 1/10] Storing in Neo4j...
[Chunk 1/10] ✓ Complete
[Chunk 2/10] Memory: 25.5%
[Chunk 2/10] Generating embedding...
[Chunk 2/10] Storing in Neo4j...
[Chunk 2/10] ✓ Complete
... (continues slowly, one at a time)
```

### Memory Pattern:
```
Start: 24%
After chunk 1: 25%
After chunk 2: 25%  ← Should stabilize, not keep growing
After chunk 3: 25%
After chunk 4: 26%
...
End: 26% (slight increase is normal)
```

### Timing:
- 10 chunks × 2 seconds = ~20 seconds minimum
- Plus embedding time (~1-2 seconds each)
- **Total: ~40-50 seconds for 10 chunks**

This is SLOW but SAFE for your laptop.

## If Still Crashing

Try even more extreme limits:

```python
# In graphrag_service.py line 224
max_content_size = 15_000  # 15KB only

# In graphrag_service.py line 236
max_chunks = 5  # Only 5 chunks

# In graphrag_service.py line 298
await asyncio.sleep(3.0)  # 3 second delay
```

## Temporary Option: Disable Embeddings

If you want to test without embeddings (will break search):

In `graphrag_service.py` around line 284:
```python
# TEMPORARY: Skip embeddings for testing
embedding = []  # Empty list instead of await self.ollama.embeddings(chunk_text)
```

This will let you test if Ollama is the bottleneck.

## Files Modified
- ✅ app/services/graphrag_service.py - Sequential processing
- ✅ app/config.py - Reduced limits
- ✅ app/routers/documents.py - Progress updates
- ✅ app/models/schemas.py - Added progress_message field

## Server Status
✅ Running at http://127.0.0.1:8000

Try uploading a VERY small document (< 500KB) and monitor:
```bash
watch -n 1 'free -h && echo "---" && tail -5 /path/to/logs'
```
