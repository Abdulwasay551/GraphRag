"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout: int = 120
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True
    
    # GraphRAG Configuration  
    max_search_results: int = 10
    max_graph_depth: int = 2
    chunk_size: int = 500  # Larger chunks = fewer chunks total
    chunk_overlap: int = 50  # Larger overlap to compensate
    
    # Memory Management (SAFE MODE - MINIMAL OLLAMA)
    chunk_batch_size: int = 1
    max_csv_rows: int = 100
    max_parse_size_mb: int = 1  # 1MB max
    memory_limit_percent: float = 60.0  # Reject at 60%
    memory_emergency_stop: float = 70.0  # Kill at 70%
    
    # LLM/Ollama Control - SMART FILE TYPE HANDLING
    enable_embeddings: bool = False  # PDF/DOCX only, if enabled
    # Note: CSV/Excel NEVER use embeddings (already structured)
    # Note: TXT/MD don't use embeddings by default (simple storage)
    enable_entity_extraction: bool = False  # Disabled - too expensive
    
    # Authentication & Security
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    
    # Redis Configuration (for background tasks)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # File Upload Configuration
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 2  # 2MB max (conservative)
    # Structured data (CSV/Excel) = safe, no LLM needed
    # Text files (TXT/MD/JSON) = safe, simple storage
    # Documents (PDF/DOCX) = can use LLM if enabled
    allowed_extensions: list = ["txt", "md", "json", "csv", "xlsx", "xls", "pdf", "docx"]
    
    # Workspace Limits
    free_plan_max_nodes: int = 1000
    pro_plan_max_nodes: int = 50000
    enterprise_plan_max_nodes: int = -1  # unlimited
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
