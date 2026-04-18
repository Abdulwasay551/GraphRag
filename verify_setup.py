"""
Simple verification script to test the GraphRAG setup
"""
import sys
import subprocess


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("  ⚠ Warning: Python 3.10+ recommended")
    return True


def check_file_exists(filepath):
    """Check if a file exists"""
    import os
    return os.path.exists(filepath)


def check_imports():
    """Check if required packages can be imported"""
    packages = [
        ('fastapi', 'FastAPI'),
        ('neo4j', 'Neo4j Driver'),
        ('httpx', 'HTTPX'),
        ('pydantic', 'Pydantic'),
        ('jinja2', 'Jinja2'),
    ]
    
    all_ok = True
    for package, name in packages:
        try:
            __import__(package)
            print(f"✓ {name} installed")
        except ImportError:
            print(f"✗ {name} NOT installed")
            all_ok = False
    
    return all_ok


def check_services():
    """Check if services are running"""
    import socket
    
    services = [
        ('Neo4j', 'localhost', 7687),
        ('Ollama', 'localhost', 11434),
    ]
    
    for name, host, port in services:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ {name} is running on port {port}")
        else:
            print(f"✗ {name} is NOT running on port {port}")


def main():
    """Run all checks"""
    print("=" * 50)
    print("GraphRAG Setup Verification")
    print("=" * 50)
    print()
    
    print("1. Python Version:")
    check_python_version()
    print()
    
    print("2. Project Files:")
    files = [
        'app/main.py',
        'app/config.py',
        'app/services/neo4j_service.py',
        'app/services/ollama_service.py',
        'app/services/graphrag_service.py',
        'requirements.txt',
        '.env',
    ]
    
    for f in files:
        if check_file_exists(f):
            print(f"✓ {f}")
        else:
            print(f"✗ {f} NOT FOUND")
    print()
    
    print("3. Python Packages:")
    check_imports()
    print()
    
    print("4. External Services:")
    check_services()
    print()
    
    print("=" * 50)
    print("Verification Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. If packages are missing: pip install -r requirements.txt")
    print("2. If Neo4j is not running: docker-compose up -d")
    print("3. If Ollama is not running: ollama serve")
    print("4. Initialize database: python scripts/init_db.py")
    print("5. Seed data: python scripts/seed_sample_data.py")
    print("6. Start app: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
