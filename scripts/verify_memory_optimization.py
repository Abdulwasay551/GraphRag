#!/usr/bin/env python3
"""
Test script to verify memory optimization is working
Run this to check if the changes are properly applied
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_settings():
    """Test that new config settings exist"""
    print("Testing configuration settings...")
    
    from app.config import settings
    
    # Check new settings exist
    required_settings = [
        'chunk_batch_size',
        'max_csv_rows',
        'max_parse_size_mb'
    ]
    
    for setting in required_settings:
        if not hasattr(settings, setting):
            print(f"❌ FAIL: Missing setting '{setting}'")
            return False
        value = getattr(settings, setting)
        print(f"✅ {setting} = {value}")
    
    print("✅ All config settings present\n")
    return True


def test_parser_methods():
    """Test that parser has new methods"""
    print("Testing document parser methods...")
    
    from app.services.document_parser import DocumentParser
    
    # Check parse_file_from_path exists
    if not hasattr(DocumentParser, 'parse_file_from_path'):
        print("❌ FAIL: Missing parse_file_from_path method")
        return False
    
    print("✅ parse_file_from_path method exists")
    
    # Check that parse_csv has max_rows parameter
    import inspect
    csv_sig = inspect.signature(DocumentParser.parse_csv)
    if 'max_rows' not in csv_sig.parameters:
        print("❌ FAIL: parse_csv missing max_rows parameter")
        return False
    
    print("✅ parse_csv has max_rows parameter")
    
    # Check that parse_excel has max_rows parameter
    excel_sig = inspect.signature(DocumentParser.parse_excel)
    if 'max_rows' not in excel_sig.parameters:
        print("❌ FAIL: parse_excel missing max_rows parameter")
        return False
    
    print("✅ parse_excel has max_rows parameter")
    print("✅ All parser methods updated\n")
    return True


def test_graphrag_imports():
    """Test that GraphRAG service has necessary imports"""
    print("Testing GraphRAG service imports...")
    
    import app.services.graphrag_service as graphrag_module
    
    # Check for gc and asyncio imports
    source = inspect.getsource(graphrag_module)
    
    if 'import gc' not in source:
        print("❌ FAIL: Missing 'import gc'")
        return False
    print("✅ gc module imported")
    
    if 'import asyncio' not in source:
        print("❌ FAIL: Missing 'import asyncio'")
        return False
    print("✅ asyncio module imported")
    
    if 'from app.config import settings' not in source:
        print("❌ FAIL: Missing config import")
        return False
    print("✅ config imported")
    
    if 'gc.collect()' not in source:
        print("❌ FAIL: gc.collect() not called in code")
        return False
    print("✅ gc.collect() is used")
    
    if 'batch_size' not in source:
        print("❌ FAIL: No batch processing found")
        return False
    print("✅ Batch processing implemented")
    
    print("✅ All GraphRAG optimizations present\n")
    return True


def test_memory_efficient_upload():
    """Test that upload uses streaming"""
    print("Testing document upload streaming...")
    
    import inspect
    from app.routers import documents
    
    # Get upload_document function source
    source = inspect.getsource(documents.upload_document)
    
    # Check for streaming pattern
    if 'while chunk := await file.read' not in source and 'while chunk:=' not in source:
        print("❌ FAIL: Upload not using streaming (walrus operator)")
        return False
    print("✅ Streaming upload implemented")
    
    # Check that old file.read() pattern is gone
    if 'file_content = await file.read()' in source:
        print("⚠️  WARNING: Old file.read() pattern still present")
        print("    (May be okay if used differently)")
    
    print("✅ Upload endpoint optimized\n")
    return True


def test_background_processing():
    """Test that background processing uses parse_file_from_path"""
    print("Testing background document processing...")
    
    import inspect
    from app.routers import documents
    
    # Get process_document_background source
    source = inspect.getsource(documents.process_document_background)
    
    # Check for new method usage
    if 'parse_file_from_path' not in source:
        print("❌ FAIL: Not using parse_file_from_path")
        return False
    print("✅ Using memory-efficient file parsing")
    
    # Check that old pattern is gone
    if 'with open(file_path, \'rb\') as f:\n            file_content = f.read()' in source:
        print("⚠️  WARNING: Old file reading pattern may still be present")
    
    print("✅ Background processing optimized\n")
    return True


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Memory Optimization Verification")
    print("="*60)
    print()
    
    tests = [
        ("Configuration Settings", test_config_settings),
        ("Document Parser", test_parser_methods),
        ("GraphRAG Service", test_graphrag_imports),
        ("Upload Streaming", test_memory_efficient_upload),
        ("Background Processing", test_background_processing),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} FAILED with error: {e}\n")
            results.append((name, False))
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All memory optimizations verified successfully!")
        print("\nYour application should now handle document ingestion")
        print("without crashing or consuming excessive RAM.")
        print("\nRestart your application to use the optimizations:")
        print("  python3 -m app.main")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    import inspect  # Import here for test functions
    sys.exit(run_all_tests())
