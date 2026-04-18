"""Health monitoring endpoint with memory stats"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.middleware import get_memory_stats
from app.services.neo4j_service import Neo4jService
import gc

router = APIRouter(prefix="/api/health", tags=["Health"])


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


@router.get("/", response_model=Dict[str, Any])
async def health_check(neo4j: Neo4jService = Depends(get_neo4j_service)):
    """Health check endpoint with memory stats"""
    
    # Get memory stats
    mem_stats = get_memory_stats()
    
    # Check Neo4j connectivity
    neo4j_healthy = False
    try:
        if neo4j and neo4j.driver:
            await neo4j.driver.verify_connectivity()
            neo4j_healthy = True
    except Exception:
        pass
    
    return {
        "status": "healthy" if neo4j_healthy else "degraded",
        "neo4j": neo4j_healthy,
        "memory": {
            "percent": round(mem_stats["memory_percent"], 2),
            "used_gb": round(mem_stats["memory_used_gb"], 2),
            "total_gb": round(mem_stats["memory_total_gb"], 2),
            "available_gb": round(mem_stats["memory_available_gb"], 2),
            "status": "critical" if mem_stats["memory_percent"] > 90 else 
                     "warning" if mem_stats["memory_percent"] > 80 else "ok"
        },
        "swap": {
            "percent": round(mem_stats["swap_percent"], 2),
            "used_gb": round(mem_stats["swap_used_gb"], 2),
            "total_gb": round(mem_stats["swap_total_gb"], 2)
        }
    }


@router.post("/gc", response_model=Dict[str, Any])
async def force_garbage_collection():
    """Force garbage collection (admin only in production)"""
    
    # Get memory before
    before = get_memory_stats()
    
    # Force aggressive GC
    gc.collect()
    gc.collect()
    gc.collect()
    
    # Get memory after
    after = get_memory_stats()
    
    freed_mb = (before["memory_used_gb"] - after["memory_used_gb"]) * 1024
    
    return {
        "status": "completed",
        "before": {
            "memory_percent": round(before["memory_percent"], 2),
            "memory_used_gb": round(before["memory_used_gb"], 2)
        },
        "after": {
            "memory_percent": round(after["memory_percent"], 2),
            "memory_used_gb": round(after["memory_used_gb"], 2)
        },
        "freed_mb": round(freed_mb, 2)
    }
