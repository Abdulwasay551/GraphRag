"""Query router for GraphRAG operations"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import QueryRequest, QueryResponse, IngestRequest, IngestResponse
from app.services.graphrag_service import GraphRAGService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["Query"])


def get_graphrag_service():
    """Dependency to get GraphRAG service instance"""
    from app.main import graphrag_service
    return graphrag_service


@router.post("/", response_model=QueryResponse)
@router.post("/ask", response_model=QueryResponse)
async def query_knowledge_graph(
    request: QueryRequest,
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """
    Query the knowledge graph using GraphRAG.
    
    This endpoint:
    1. Generates embeddings for the query
    2. Finds semantically similar nodes
    3. Expands to neighboring nodes for context
    4. Uses LLM to generate an answer with graph context
    """
    try:
        result = await service.query(
            user_query=request.query,
            max_depth=request.max_depth,
            top_k=request.top_k
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Query endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    service: GraphRAGService = Depends(get_graphrag_service)
):
    """
    Ingest a document into the knowledge graph.
    
    This endpoint:
    1. Chunks the document
    2. Generates embeddings
    3. Extracts entities and relationships
    4. Stores everything in Neo4j
    """
    try:
        from app.config import settings
        
        chunk_size = request.chunk_size or settings.chunk_size
        
        result = await service.ingest_document(
            content=request.content,
            metadata=request.metadata,
            chunk_size=chunk_size
        )
        
        return IngestResponse(**result)
        
    except Exception as e:
        logger.error(f"Ingest endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
