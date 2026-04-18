"""Pydantic schemas for API requests and responses"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class GraphNode(BaseModel):
    """Graph node representation"""
    id: str
    label: str
    properties: Dict[str, Any] = {}
    score: Optional[float] = None


class GraphRelationship(BaseModel):
    """Graph relationship representation"""
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = {}


class GraphData(BaseModel):
    """Complete graph data structure"""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]


class QueryRequest(BaseModel):
    """GraphRAG query request"""
    query: str = Field(..., min_length=1, description="The question to ask")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum graph traversal depth")
    top_k: int = Field(10, ge=1, le=50, description="Number of relevant nodes to retrieve")


class QueryResponse(BaseModel):
    """GraphRAG query response"""
    query: str
    answer: str
    context_nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    sources: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IngestRequest(BaseModel):
    """Document ingestion request"""
    content: str = Field(..., min_length=1, description="Document content to ingest")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    chunk_size: Optional[int] = Field(None, description="Override default chunk size")


class IngestResponse(BaseModel):
    """Document ingestion response"""
    status: str
    chunks_created: int
    nodes_created: int
    relationships_created: int
    message: str


class GraphStats(BaseModel):
    """Graph database statistics"""
    total_nodes: int
    total_relationships: int
    node_labels: Dict[str, int]
    relationship_types: Dict[str, int]


class HealthStatus(BaseModel):
    """Health check status"""
    status: str
    neo4j_connected: bool
    ollama_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Authentication & User Management Schemas
# ============================================================================

class UserRole(str, Enum):
    """User roles for RBAC"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class WorkspacePlan(str, Enum):
    """Workspace subscription plans"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserCreate(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=1)


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response (without password)"""
    id: str
    email: str
    full_name: str
    created_at: datetime
    is_active: bool = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: str
    email: str


class WorkspaceCreate(BaseModel):
    """Workspace creation request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Workspace response"""
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    plan: WorkspacePlan = WorkspacePlan.FREE
    created_at: datetime
    node_count: int = 0
    relationship_count: int = 0


class WorkspaceMember(BaseModel):
    """Workspace member"""
    user_id: str
    email: str
    full_name: str
    role: UserRole
    added_at: datetime


class APIKey(BaseModel):
    """API key for workspace"""
    id: str
    workspace_id: str
    key: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True


# ============================================================================
# Document Upload & Processing Schemas
# ============================================================================

class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    HTML = "html"


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    document_id: str
    filename: str
    file_type: DocumentType
    size_bytes: int
    status: DocumentStatus
    uploaded_at: datetime


class DocumentProcessingStatus(BaseModel):
    """Document processing status"""
    document_id: str
    status: DocumentStatus
    progress: int = Field(ge=0, le=100, description="Processing progress percentage")
    progress_message: Optional[str] = None
    chunks_processed: int = 0
    entities_extracted: int = 0
    relationships_extracted: int = 0
    error_message: Optional[str] = None


class DocumentListItem(BaseModel):
    """Document list item"""
    document_id: str
    filename: str
    file_type: DocumentType
    size_bytes: int
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


# ============================================================================
# Custom Schema Builder Schemas
# ============================================================================

class EntityTypeCreate(BaseModel):
    """Custom entity type definition"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    color: str = "#3B82F6"  # Default blue color
    properties: List[Dict[str, str]] = Field(default_factory=list)


class RelationshipTypeCreate(BaseModel):
    """Custom relationship type definition"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    source_entity_types: List[str] = Field(default_factory=list)
    target_entity_types: List[str] = Field(default_factory=list)


class WorkspaceSchema(BaseModel):
    """Complete workspace schema"""
    workspace_id: str
    entity_types: List[EntityTypeCreate]
    relationship_types: List[RelationshipTypeCreate]
    updated_at: datetime


# ============================================================================
# AI-Assisted Review Schemas
# ============================================================================

class ExtractedEntity(BaseModel):
    """Entity extracted by AI"""
    entity_id: str
    name: str
    type: str
    properties: Dict[str, Any] = {}
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str
    reviewed: bool = False
    approved: bool = False


class ExtractedRelationship(BaseModel):
    """Relationship extracted by AI"""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    type: str
    properties: Dict[str, Any] = {}
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str
    reviewed: bool = False
    approved: bool = False


class ReviewBatchRequest(BaseModel):
    """Batch review request"""
    document_id: str
    entity_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    relationship_decisions: List[Dict[str, Any]] = Field(default_factory=list)


class ReviewBatchResponse(BaseModel):
    """Batch review response"""
    entities_approved: int
    entities_rejected: int
    relationships_approved: int
    relationships_rejected: int
    graph_updated: bool


# ============================================================================
# Export & GraphQL Schemas
# ============================================================================

class ExportFormat(str, Enum):
    """Export format options"""
    CSV = "csv"
    JSON = "json"
    GRAPHML = "graphml"
    CYPHER = "cypher"


class ExportRequest(BaseModel):
    """Export request"""
    format: ExportFormat
    include_labels: Optional[List[str]] = None
    include_relationship_types: Optional[List[str]] = None
    max_nodes: Optional[int] = None


class ExportResponse(BaseModel):
    """Export response"""
    export_id: str
    format: ExportFormat
    download_url: str
    created_at: datetime
    expires_at: datetime


# ============================================================================
# Chatbot Widget Schemas
# ============================================================================

class ChatbotSettings(BaseModel):
    """Chatbot widget settings"""
    workspace_id: str
    title: str = "AI Assistant"
    primary_color: str = "#3B82F6"
    position: str = "bottom-right"  # bottom-right, bottom-left, etc.
    greeting_message: str = "Hello! How can I help you today?"
    placeholder_text: str = "Ask a question..."
    max_depth: int = Field(2, ge=1, le=5)
    top_k: int = Field(10, ge=1, le=50)


class ChatbotSettingsResponse(BaseModel):
    """Chatbot settings response"""
    workspace_id: str
    settings: ChatbotSettings
    embed_code: str
    updated_at: datetime


class ChatMessage(BaseModel):
    """Chat message"""
    message: str
    workspace_id: str
    api_key: str


class ChatResponse(BaseModel):
    """Chat response"""
    message: str
    answer: str
    sources: List[str]
    timestamp: datetime

