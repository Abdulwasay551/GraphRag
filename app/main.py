"""FastAPI GraphRAG Application"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import gc
from app.config import settings
from app.services.neo4j_service import Neo4jService
from app.services.ollama_service import OllamaService
from app.services.graphrag_service import GraphRAGService
from app.services.workspace_service import WorkspaceService
from app.middleware import MemoryMonitorMiddleware, get_memory_stats
from app.routers import query, visualization, auth, documents, schema, export, chatbot, contact, health
from app.models.schemas import HealthStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
neo4j_service: Neo4jService = None
ollama_service: OllamaService = None
graphrag_service: GraphRAGService = None
workspace_service: WorkspaceService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global neo4j_service, ollama_service, graphrag_service, workspace_service
    
    logger.info("Starting GraphRAG application...")
    
    # Log initial memory state
    mem_stats = get_memory_stats()
    logger.info(f"Initial memory: {mem_stats['memory_used_gb']:.2f}GB / {mem_stats['memory_total_gb']:.2f}GB ({mem_stats['memory_percent']:.1f}%)")
    
    # Force garbage collection before starting
    gc.collect()
    
    # Initialize services
    try:
        # Neo4j service
        neo4j_service = Neo4jService(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database
        )
        await neo4j_service.connect()
        logger.info("Neo4j service initialized")
        
        # Ollama service
        ollama_service = OllamaService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout
        )
        logger.info("Ollama service initialized")
        
        # GraphRAG service
        graphrag_service = GraphRAGService(neo4j_service, ollama_service)
        logger.info("GraphRAG service initialized")
        
        # Workspace service
        workspace_service = WorkspaceService(neo4j_service)
        logger.info("Workspace service initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down GraphRAG application...")
    if neo4j_service:
        await neo4j_service.close()
    if ollama_service:
        await ollama_service.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="GraphRAG API",
    description="Graph Retrieval-Augmented Generation API with Neo4j and Ollama",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory monitoring middleware (CRITICAL for preventing crashes)
app.add_middleware(
    MemoryMonitorMiddleware,
    max_memory_percent=settings.memory_limit_percent
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(visualization.router)
app.include_router(documents.router)
app.include_router(schema.router)
app.include_router(export.router)
app.include_router(chatbot.router)
app.include_router(contact.router)


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    neo4j_ok = await neo4j_service.health_check() if neo4j_service else False
    ollama_ok = await ollama_service.health_check() if ollama_service else False
    
    status = "healthy" if neo4j_ok and ollama_ok else "unhealthy"
    
    return HealthStatus(
        status=status,
        neo4j_connected=neo4j_ok,
        ollama_connected=ollama_ok
    )


@app.get("/")
async def root():
    """Root endpoint redirects to visualization"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload
    )
