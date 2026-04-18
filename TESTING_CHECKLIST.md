# Testing Checklist: Document Ingestion Fix

Use this checklist to verify the fixes work correctly and your system stays stable.

## Pre-Testing Setup

- [ ] **Backup your data** (if you have important documents already uploaded)
  ```bash
  # Backup Neo4j if needed
  # Backup uploads folder
  cp -r uploads uploads_backup
  ```

- [ ] **Check system resources**
  ```bash
  free -h
  # Should have at least 4GB available memory
  ```

- [ ] **Restart application**
  ```bash
  cd /home/bnb/Documents/GraphRAG
  source venv/bin/activate
  
  # Kill any running instances
  pkill -f "uvicorn"
  
  # Start fresh
  uvicorn app.main:app --reload
  ```

## Test 1: Small Text File (Should Pass ✅)

- [ ] Create a small test file
  ```bash
  echo "This is a test document. It has multiple sentences. Let's see how it processes." > test_small.txt
  ```

- [ ] Upload via UI or API
  ```bash
  curl -X POST http://localhost:8000/api/documents/upload \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -F "file=@test_small.txt"
  ```

- [ ] **Expected:** 
  - Completes in < 30 seconds
  - Status changes to "completed"
  - System stays responsive

- [ ] **Actual Result:** _______________

---

## Test 2: Medium PDF (Should Pass ✅)

- [ ] Find or create a 5-10 page PDF (< 5MB)

- [ ] Upload the PDF

- [ ] Monitor system during upload:
  ```bash
  # In another terminal
  htop
  ```

- [ ] **Expected:**
  - Completes in 1-3 minutes
  - Memory stays < 50%
  - CPU usage reasonable
  - System stays responsive
  - Can use other apps while processing

- [ ] **Actual Result:** _______________

---

## Test 3: Large File Rejection (Should Reject ✅)

- [ ] Try to upload a file > 20MB

- [ ] **Expected:**
  - Gets rejected with error
  - Error message: "File too large. Maximum size: 20MB"
  - No system slowdown

- [ ] **Actual Result:** _______________

---

## Test 4: CSV File (Should Pass ✅)

- [ ] Create a test CSV with 100 rows
  ```python
  import pandas as pd
  df = pd.DataFrame({
      'name': [f'Person {i}' for i in range(100)],
      'age': [20 + i for i in range(100)],
      'city': ['New York', 'London', 'Tokyo'] * 34
  })
  df.to_csv('test_data.csv', index=False)
  ```

- [ ] Upload the CSV

- [ ] **Expected:**
  - Completes in < 2 minutes
  - All 100 rows processed
  - No memory issues

- [ ] **Actual Result:** _______________

---

## Test 5: Multiple Concurrent Uploads (Should Handle ✅)

- [ ] Upload 2-3 small files at the same time

- [ ] Monitor system resources

- [ ] **Expected:**
  - All files process successfully
  - May take slightly longer
  - System remains stable
  - No crashes

- [ ] **Actual Result:** _______________

---

## Test 6: Memory Limit Protection (Should Reject if Low Memory)

- [ ] Open several memory-intensive applications (browsers, etc.)
  until memory > 75%

- [ ] Try to upload a document

- [ ] **Expected:**
  - If memory > 75%, upload rejected with message
  - System doesn't crash
  - Can retry after closing other apps

- [ ] **Actual Result:** _______________

---

## Test 7: Search Still Works (Should Pass ✅)

- [ ] After uploading a document, try to search it

- [ ] **Expected:**
  - Search returns results
  - Results are relevant
  - Embeddings working correctly

- [ ] **Actual Result:** _______________

---

## Stress Test (Optional, Advanced)

- [ ] Upload 5 different documents in a row (one after another)

- [ ] Monitor with:
  ```bash
  # Terminal 1: Memory
  watch -n 1 free -h
  
  # Terminal 2: Logs
  tail -f logs/app.log
  
  # Terminal 3: Application
  htop
  ```

- [ ] **Expected:**
  - All 5 complete successfully
  - Memory gets cleaned up between uploads
  - No progressive memory leak
  - System stays responsive throughout

- [ ] **Actual Result:** _______________

---

## Regression Checks

### Features That Should Still Work:

- [ ] User login/registration
- [ ] Workspace creation
- [ ] Document listing
- [ ] Document deletion
- [ ] Query/search functionality
- [ ] Graph visualization
- [ ] Export functionality

---

## Red Flags 🚩

Stop testing and investigate if you see:

- ❌ System freezes for > 5 minutes
- ❌ Memory usage > 90%
- ❌ Application becomes unresponsive
- ❌ Browser tabs crash
- ❌ Files not being processed (stuck in "processing" state)
- ❌ Database errors in logs

---

## If Tests Fail

1. **Check logs first:**
   ```bash
   tail -100 logs/app.log
   ```

2. **Check if services are running:**
   ```bash
   # Neo4j
   sudo systemctl status neo4j
   
   # Ollama
   ollama list
   ```

3. **Verify config:**
   ```python
   from app.config import settings
   print(f"Max upload: {settings.max_upload_size_mb}MB")
   print(f"Max parse: {settings.max_parse_size_mb}MB")
   print(f"Memory limit: {settings.memory_limit_percent}%")
   ```

4. **Restart everything:**
   ```bash
   sudo systemctl restart neo4j
   pkill -f ollama
   ollama serve &
   pkill -f uvicorn
   uvicorn app.main:app --reload
   ```

---

## Success Criteria ✅

All tests should show:
- ✅ Fast processing (< 5 min for normal files)
- ✅ Stable memory usage
- ✅ System stays responsive
- ✅ No crashes or freezes
- ✅ Error messages for oversized files
- ✅ Documents are searchable after upload

---

## After Testing

- [ ] Clean up test files
  ```bash
  rm test_small.txt test_data.csv
  ```

- [ ] Document any issues found

- [ ] Consider adding more test files to permanent test suite

---

**Testing Date:** __________

**Tester:** __________

**Results:** PASS / FAIL / PARTIAL

**Notes:**
_______________________________________
_______________________________________
_______________________________________
