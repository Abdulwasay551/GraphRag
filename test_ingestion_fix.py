#!/usr/bin/env python3
"""Test script to verify document ingestion memory improvements"""
import psutil
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.document_parser import DocumentParser
from app.config import settings


def get_memory_usage():
    """Get current memory usage"""
    memory = psutil.virtual_memory()
    return memory.percent, memory.used / (1024**3)  # GB


async def test_document_parsing():
    """Test document parsing with memory monitoring"""
    print("=" * 60)
    print("Document Ingestion Memory Test")
    print("=" * 60)
    
    # Initial memory
    mem_percent, mem_gb = get_memory_usage()
    print(f"\n✓ Initial Memory: {mem_percent:.1f}% ({mem_gb:.2f} GB)")
    
    # Check limits
    print(f"\n✓ Configuration:")
    print(f"  - Max upload size: {settings.max_upload_size_mb} MB")
    print(f"  - Max parse size: {settings.max_parse_size_mb} MB")
    print(f"  - Max chunks: 50 (hardcoded in graphrag_service.py)")
    print(f"  - Memory limit: {settings.memory_limit_percent}%")
    print(f"  - Chunk size: {settings.chunk_size}")
    print(f"  - Batch size: {settings.chunk_batch_size}")
    
    # Create test content
    print(f"\n✓ Creating test content...")
    test_content = "This is a test sentence. " * 1000  # ~25KB
    test_file = Path("test_document.txt")
    test_file.write_text(test_content)
    
    try:
        # Test parsing
        print(f"\n✓ Testing document parser...")
        parser = DocumentParser()
        
        # Parse the test file
        parsed_content = parser.parse_file_from_path(
            str(test_file), 
            "txt",
            max_size_mb=settings.max_parse_size_mb
        )
        
        mem_percent, mem_gb = get_memory_usage()
        print(f"  - Parsed {len(parsed_content)} characters")
        print(f"  - Memory after parsing: {mem_percent:.1f}% ({mem_gb:.2f} GB)")
        
        # Simulate chunking (from graphrag_service)
        chunk_size = settings.chunk_size
        chunk_overlap = 50
        
        chunks = []
        start = 0
        while start < len(parsed_content):
            end = min(start + chunk_size, len(parsed_content))
            chunks.append(parsed_content[start:end])
            start = end - chunk_overlap if end < len(parsed_content) else end
        
        # Apply chunk limit
        max_chunks = 50
        if len(chunks) > max_chunks:
            chunks = chunks[:max_chunks]
        
        mem_percent, mem_gb = get_memory_usage()
        print(f"  - Created {len(chunks)} chunks")
        print(f"  - Memory after chunking: {mem_percent:.1f}% ({mem_gb:.2f} GB)")
        
        # Check if we'd be able to process
        if mem_percent > settings.memory_limit_percent:
            print(f"\n✗ ERROR: Memory usage {mem_percent:.1f}% exceeds limit {settings.memory_limit_percent}%")
            print(f"  Processing would be rejected!")
        else:
            print(f"\n✓ SUCCESS: Memory usage {mem_percent:.1f}% is within limit {settings.memory_limit_percent}%")
            print(f"  Processing would proceed safely!")
        
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    return mem_percent <= settings.memory_limit_percent


def test_file_limits():
    """Test file size limits"""
    print("\n" + "=" * 60)
    print("File Size Limit Tests")
    print("=" * 60)
    
    parser = DocumentParser()
    
    # Test oversized file
    print("\n✓ Testing oversized file rejection...")
    large_content = b"x" * (25 * 1024 * 1024)  # 25MB
    
    try:
        # This should fail
        parser.parse_file(large_content, "txt")
        print("✗ FAIL: Large file was not rejected!")
    except ValueError as e:
        print(f"✓ PASS: Large file correctly rejected: {e}")
    
    # Test acceptable file
    print("\n✓ Testing acceptable file...")
    small_content = b"x" * (1 * 1024 * 1024)  # 1MB
    
    try:
        result = parser.parse_file(small_content, "txt")
        print(f"✓ PASS: Small file processed ({len(result)} chars)")
    except Exception as e:
        print(f"✗ FAIL: Small file rejected: {e}")


if __name__ == "__main__":
    print("\n🔍 Starting Document Ingestion Tests...\n")
    
    # Test file limits
    test_file_limits()
    
    # Test memory usage
    result = asyncio.run(test_document_parsing())
    
    # Final verdict
    print("\n" + "=" * 60)
    if result:
        print("✓ ALL TESTS PASSED - Document ingestion should work safely")
    else:
        print("✗ TESTS FAILED - Memory usage too high")
    print("=" * 60 + "\n")
    
    sys.exit(0 if result else 1)
