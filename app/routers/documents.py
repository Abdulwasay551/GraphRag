"""Document upload and processing router"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from datetime import datetime
from pathlib import Path
import os
import asyncio
import logging
import psutil  # Add for memory monitoring

from app.models.schemas import (
    DocumentUploadResponse, DocumentProcessingStatus, DocumentListItem,
    DocumentType, DocumentStatus, TokenData
)
from app.utils.auth import get_current_user
from app.services.neo4j_service import Neo4jService
from app.services.document_parser import DocumentParser
from app.services.graphrag_service import GraphRAGService
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger(__name__)

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

# Track active background tasks
active_tasks = {}


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


def get_graphrag_service() -> GraphRAGService:
    """Dependency to get GraphRAG service instance"""
    from app.main import graphrag_service
    return graphrag_service


def get_file_type(filename: str) -> DocumentType:
    """Determine document type from filename"""
    ext = Path(filename).suffix.lower().lstrip('.')
    
    mapping = {
        'pdf': DocumentType.PDF,
        'docx': DocumentType.DOCX,
        'doc': DocumentType.DOCX,
        'txt': DocumentType.TXT,
        'csv': DocumentType.CSV,
        'json': DocumentType.JSON,
        'xlsx': DocumentType.EXCEL,
        'xls': DocumentType.EXCEL,
        'md': DocumentType.MARKDOWN,
        'markdown': DocumentType.MARKDOWN,
        'html': DocumentType.HTML,
        'htm': DocumentType.HTML,
    }
    
    return mapping.get(ext, DocumentType.TXT)


async def process_document_background(
    document_id: str,
    file_path: str,
    file_extension: str,
    workspace_id: str,
    neo4j: Neo4jService,
    graphrag: GraphRAGService
):
    """Process document in the background with AGGRESSIVE resource monitoring"""
    import gc
    
    try:
        # CRITICAL: Aggressive pre-processing cleanup
        gc.collect()
        
        # Check memory before starting - ULTRA AGGRESSIVE - SYSTEM CRASH MODE
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        logger.info(f"Starting processing for {document_id}. Memory usage: {memory_percent:.1f}%")
        
        # EMERGENCY: Reject if memory is already high - VERY LOW THRESHOLD
        if memory_percent > 30:  # ULTRA aggressive - 50% threshold (was 55%)
            error_msg = f"System memory too high ({memory_percent:.1f}%). Cannot process document safely."
            logger.error(error_msg)
            await neo4j.execute_query(
                """
                MATCH (d:Document {id: $document_id})
                SET d.status = 'failed', d.error_message = $error
                """,
                {"document_id": document_id, "error": error_msg}
            )
            return
        
        logger.info(f"Starting background processing for document {document_id}")
        
        # Update status to processing with progress tracking
        await neo4j.execute_query(
            """
            MATCH (d:Document {id: $document_id})
            SET d.status = 'processing', 
                d.started_at = datetime(),
                d.progress = 0,
                d.progress_message = 'Starting document parsing...',
                d.chunks_processed = 0
            """,
            {"document_id": document_id}
        )
        
        # Check file size before parsing
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > settings.max_parse_size_mb:
            raise ValueError(f"File size {file_size_mb:.1f}MB exceeds parsing limit of {settings.max_parse_size_mb}MB")
        
        logger.info(f"Parsing {file_size_mb:.1f}MB file...")
        
        # Force cleanup before parsing
        import gc
        gc.collect()
        
        # Parse document - CSV/Excel now safe with csv module & iloc
        parser = DocumentParser()
        text_content = parser.parse_file_from_path(file_path, file_extension)
        
        # Check memory after parsing - ULTRA AGGRESSIVE
        memory = psutil.virtual_memory()
        logger.info(f"After parsing - Memory: {memory.percent:.1f}%, Content size: {len(text_content)} chars")
        
        # Force GC immediately after parsing
        gc.collect()
        
        if memory.percent > 60:  # Lower threshold - 60% (was 70%)
            error_msg = f"Memory critical after parsing ({memory.percent:.1f}%). Aborting."
            logger.error(error_msg)
            # Cleanup parsed content
            del text_content
            gc.collect()
            raise MemoryError(error_msg)
        
        # Update progress: parsing complete, starting ingestion
        await neo4j.execute_query(
            """
            MATCH (d:Document {id: $document_id})
            SET d.progress = 10, d.progress_message = 'Parsing complete, starting ingestion...'
            """,
            {"document_id": document_id}
        )
        
        logger.info(f"Document parsed ({len(text_content)} chars), starting GraphRAG ingestion for {document_id}")
        
        # Check if metadata-only mode
        is_metadata_only = file_extension.lower() in ['csv', 'xlsx', 'xls']
        
        # Ingest into GraphRAG with resource limits and file type info
        result = await graphrag.ingest_document(
            content=text_content,
            metadata={
                "document_id": document_id,
                "workspace_id": workspace_id,
                "metadata_only": is_metadata_only
            },
            file_type=file_extension  # Pass file type for smart processing
        )
        
        logger.info(f"Document {document_id} ingestion completed successfully")
        
        # Log final memory state
        memory_after = psutil.virtual_memory()
        logger.info(f"After ingestion - Memory: {memory_after.percent:.1f}%")
        
        # Cleanup content immediately
        del text_content
        import gc
        gc.collect()
        
        # Update document status
        await neo4j.execute_query(
            """
            MATCH (d:Document {id: $document_id})
            MATCH (w:Workspace {id: $workspace_id})
            SET d.status = 'completed',
                d.processed_at = datetime(),
                d.chunks_processed = $chunks,
                d.entities_extracted = $nodes,
                d.relationships_extracted = $relationships
            CREATE (d)-[:IN_WORKSPACE]->(w)
            """,
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "chunks": result.get("chunks_created", 0),
                "nodes": result.get("nodes_created", 0),
                "relationships": result.get("relationships_created", 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {str(e)}", exc_info=True)
        
        # CRITICAL: Cleanup on error to prevent memory leak
        import gc
        gc.collect()
        memory = psutil.virtual_memory()
        logger.info(f"After error cleanup - Memory: {memory.percent:.1f}%")
        
        # Update status to failed
        try:
            await neo4j.execute_query(
                """
                MATCH (d:Document {id: $document_id})
                SET d.status = 'failed', d.error_message = $error
                """,
                {"document_id": document_id, "error": str(e)}
            )
        except Exception as db_error:
            logger.error(f"Failed to update document status: {str(db_error)}")
    finally:
        # CRITICAL: Always cleanup and remove from active tasks
        if document_id in active_tasks:
            del active_tasks[document_id]
        
        import gc
        gc.collect()  # Final cleanup
        
        memory_final = psutil.virtual_memory()
        logger.info(f"Background processing completed for {document_id}. Final memory: {memory_final.percent:.1f}%")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service),
    graphrag: GraphRAGService = Depends(get_graphrag_service),
    workspace_id: str = Form("")
):
    """Upload a document for processing (processing happens in background)"""
    
    # CRITICAL: Check memory BEFORE accepting upload
    import psutil
    mem_now = psutil.virtual_memory().percent
    if mem_now > 45:  # Reasonable threshold - 45% (was 25%)
        raise HTTPException(
            status_code=503,
            detail=f"System memory too high ({mem_now:.1f}%). Cannot accept uploads. Try again later."
        )
    
    # If no workspace_id provided or empty string, get user's first workspace
    if not workspace_id or workspace_id.strip() == "":
        default_workspace_query = """
        MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace)
        RETURN w.id as id
        ORDER BY w.created_at DESC
        LIMIT 1
        """
        default_result = await neo4j.execute_query(default_workspace_query, {
            "user_id": current_user.user_id
        })
        
        if not default_result or not default_result[0].get('id'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workspace found. Please create a workspace first."
            )
        
        workspace_id = default_result[0]['id']
    
    # Verify workspace access
    workspace_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    workspace_result = await neo4j.execute_query(workspace_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not workspace_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {', '.join(settings.allowed_extensions)}"
        )
    
    # Create document record first
    document_id = str(uuid.uuid4())
    file_type = get_file_type(file.filename)
    uploaded_at = datetime.utcnow()
    
    # Stream file to disk to avoid loading entire file in memory
    file_path = os.path.join(settings.upload_dir, f"{document_id}_{file.filename}")
    file_size = 0
    max_size = settings.max_upload_size_mb * 1024 * 1024
    
    # Stream in chunks
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(file_path, 'wb') as f:
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > max_size:
                # Clean up file
                f.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                )
            f.write(chunk)
    
    # Create document node WITH workspace relationship immediately
    create_doc_query = """
    MATCH (w:Workspace {id: $workspace_id})
    MATCH (u:User {id: $user_id})
    CREATE (d:Document {
        id: $document_id,
        filename: $filename,
        file_type: $file_type,
        size_bytes: $size_bytes,
        file_path: $file_path,
        status: $status,
        uploaded_at: datetime($uploaded_at),
        uploaded_by: $user_id
    })
    CREATE (d)-[:IN_WORKSPACE]->(w)
    CREATE (d)-[:UPLOADED_BY]->(u)
    RETURN d
    """
    
    await neo4j.execute_query(create_doc_query, {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "filename": file.filename,
        "file_type": file_type.value,
        "size_bytes": file_size,
        "file_path": file_path,
        "status": DocumentStatus.PENDING.value,
        "uploaded_at": uploaded_at.isoformat(),
        "user_id": current_user.user_id
    })
    
    # Start background processing as a fire-and-forget task
    task = asyncio.create_task(
        process_document_background(
            document_id,
            file_path,
            file_ext,
            workspace_id,
            neo4j,
            graphrag
        )
    )
    
    # Track the task
    active_tasks[document_id] = task
    
    logger.info(f"Document {document_id} uploaded successfully, processing started in background")
    
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        file_type=file_type,
        size_bytes=file_size,
        status=DocumentStatus.PENDING,
        uploaded_at=uploaded_at
    )


@router.get("/{document_id}/status", response_model=DocumentProcessingStatus)
async def get_document_status(
    document_id: str,
    workspace_id: str = None,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get document processing status"""
    
    # Handle null/missing workspace_id - just check document belongs to user
    if not workspace_id or workspace_id == "null":
        query = """
        MATCH (d:Document {id: $document_id})-[:UPLOADED_BY]->(u:User {id: $user_id})
        RETURN d
        """
        result = await neo4j.execute_query(query, {
            "document_id": document_id,
            "user_id": current_user.user_id
        })
    else:
        query = """
        MATCH (d:Document {id: $document_id})-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
        MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w)
        RETURN d
        """
        result = await neo4j.execute_query(query, {
            "document_id": document_id,
            "workspace_id": workspace_id,
            "user_id": current_user.user_id
        })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or no access"
        )
    
    doc = result[0]["d"]
    
    # Calculate progress based on status and actual progress field
    progress = doc.get("progress", 0)
    if doc.get("status") == "completed":
        progress = 100
    elif doc.get("status") == "failed":
        progress = 0
    elif doc.get("status") == "pending":
        progress = 0
    
    return DocumentProcessingStatus(
        document_id=doc["id"],
        status=DocumentStatus(doc.get("status", "pending")),
        progress=progress,
        chunks_processed=doc.get("chunks_processed", 0),
        entities_extracted=doc.get("entities_extracted", 0),
        relationships_extracted=doc.get("relationships_extracted", 0),
        error_message=doc.get("error_message"),
        progress_message=doc.get("progress_message", "")
    )


@router.get("/active-tasks")
async def get_active_tasks(
    current_user: TokenData = Depends(get_current_user)
):
    """Get list of currently processing documents"""
    return {
        "active_tasks": list(active_tasks.keys()),
        "count": len(active_tasks)
    }


@router.get("/list")
async def list_documents(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """List all documents in a workspace"""
    
    query = """
    MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w)
    RETURN d
    ORDER BY d.uploaded_at DESC
    """
    
    results = await neo4j.execute_query(query, {
        "workspace_id": workspace_id,
        "user_id": current_user.user_id
    })
    
    documents = []
    for record in results:
        doc = record["d"]
        
        # Convert Neo4j DateTime to Python datetime
        uploaded_at = doc["uploaded_at"]
        if hasattr(uploaded_at, 'to_native'):
            uploaded_at = uploaded_at.to_native()
        
        processed_at = doc.get("processed_at")
        if processed_at and hasattr(processed_at, 'to_native'):
            processed_at = processed_at.to_native()
        
        documents.append(DocumentListItem(
            document_id=doc["id"],
            filename=doc["filename"],
            file_type=DocumentType(doc["file_type"]),
            size_bytes=doc["size_bytes"],
            status=DocumentStatus(doc.get("status", "pending")),
            uploaded_at=uploaded_at,
            processed_at=processed_at
        ))
    
    return {"documents": documents}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Delete a document and its associated data"""
    
    # Get document info
    query = """
    MATCH (d:Document {id: $document_id})-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w)
    RETURN d.file_path as file_path
    """
    
    result = await neo4j.execute_query(query, {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "user_id": current_user.user_id
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or no access"
        )
    
    file_path = result[0].get("file_path")
    
    # Delete file from disk
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Continue even if file deletion fails
    
    # Delete document node and related data
    delete_query = """
    MATCH (d:Document {id: $document_id})-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
    OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(chunk)
    DETACH DELETE chunk, d
    """
    
    await neo4j.execute_query(delete_query, {
        "document_id": document_id,
        "workspace_id": workspace_id
    })
    
    return {"status": "success", "message": "Document deleted"}
