"""Memory monitoring middleware to prevent crashes"""
import psutil
import gc
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class MemoryMonitorMiddleware(BaseHTTPMiddleware):
    """Monitor memory usage and reject requests if too high"""
    
    def __init__(self, app, max_memory_percent: float = 85.0):
        super().__init__(app)
        self.max_memory_percent = max_memory_percent
        self.request_count = 0
        
    async def dispatch(self, request: Request, call_next):
        """Check memory before processing request"""
        
        self.request_count += 1
        
        # Check memory every request
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Log memory usage periodically
        if self.request_count % 10 == 0:
            logger.info(f"Memory usage: {memory_percent:.1f}% ({memory.used / 1024**3:.2f}GB / {memory.total / 1024**3:.2f}GB)")
        
        # If memory is critically high, reject request and force GC
        if memory_percent > self.max_memory_percent:
            logger.error(f"Memory usage too high: {memory_percent:.1f}%")
            
            # Force aggressive garbage collection
            gc.collect()
            gc.collect()
            gc.collect()
            
            # Check again after GC
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > self.max_memory_percent:
                logger.error(f"Still high after GC: {memory_percent:.1f}%")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "detail": "System memory usage too high. Please try again in a moment.",
                        "memory_percent": memory_percent
                    }
                )
            else:
                logger.info(f"Memory freed by GC: now at {memory_percent:.1f}%")
        
        # Process request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request error: {e}")
            # Force GC on error
            gc.collect()
            raise
        finally:
            # Periodic aggressive GC
            if self.request_count % 50 == 0:
                gc.collect()
                logger.info("Periodic garbage collection completed")


def get_memory_stats() -> dict:
    """Get current memory statistics"""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        "memory_percent": memory.percent,
        "memory_used_gb": memory.used / 1024**3,
        "memory_total_gb": memory.total / 1024**3,
        "memory_available_gb": memory.available / 1024**3,
        "swap_percent": swap.percent,
        "swap_used_gb": swap.used / 1024**3,
        "swap_total_gb": swap.total / 1024**3
    }


async def check_memory_before_operation(operation_name: str, min_free_gb: float = 2.0):
    """Check if enough memory is available before expensive operation"""
    memory = psutil.virtual_memory()
    available_gb = memory.available / 1024**3
    
    if available_gb < min_free_gb:
        logger.warning(f"Low memory before {operation_name}: {available_gb:.2f}GB available")
        
        # Try garbage collection
        gc.collect()
        gc.collect()
        
        memory = psutil.virtual_memory()
        available_gb = memory.available / 1024**3
        
        if available_gb < min_free_gb:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Insufficient memory for operation. Available: {available_gb:.2f}GB, Required: {min_free_gb:.2f}GB"
            )
    
    return available_gb
