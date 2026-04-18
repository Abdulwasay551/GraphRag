"""Embeddable chatbot widget router"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from datetime import datetime
import uuid

from app.models.schemas import (
    ChatbotSettings, ChatbotSettingsResponse, ChatMessage, ChatResponse,
    TokenData, QueryRequest
)
from app.utils.auth import get_current_user
from app.services.neo4j_service import Neo4jService
from app.services.graphrag_service import GraphRAGService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot Widget"])


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


def get_graphrag_service() -> GraphRAGService:
    """Dependency to get GraphRAG service instance"""
    from app.main import graphrag_service
    return graphrag_service


def get_workspace_service() -> WorkspaceService:
    """Dependency to get Workspace service instance"""
    from app.main import workspace_service
    return workspace_service


@router.get("/{workspace_id}/settings", response_model=ChatbotSettingsResponse)
async def get_chatbot_settings(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get chatbot widget settings"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    OPTIONAL MATCH (w)-[:HAS_CHATBOT_SETTINGS]->(s:ChatbotSettings)
    RETURN w, s
    """
    
    result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    w = result[0]["w"]
    s = result[0].get("s")
    
    # Use default settings if none exist
    if s:
        settings = ChatbotSettings(
            workspace_id=workspace_id,
            title=s.get("title", "AI Assistant"),
            primary_color=s.get("primary_color", "#3B82F6"),
            position=s.get("position", "bottom-right"),
            greeting_message=s.get("greeting_message", "Hello! How can I help you today?"),
            placeholder_text=s.get("placeholder_text", "Ask a question..."),
            max_depth=s.get("max_depth", 2),
            top_k=s.get("top_k", 10)
        )
    else:
        settings = ChatbotSettings(workspace_id=workspace_id)
    
    # Generate embed code
    embed_code = f"""
<!-- GraphRAG Chatbot Widget -->
<script>
  (function() {{
    var chatbotConfig = {{
      workspaceId: '{workspace_id}',
      apiKey: 'YOUR_API_KEY',  // Replace with your API key
      apiUrl: '{Request.base_url if hasattr(Request, "base_url") else "http://localhost:8000"}'
    }};
    var script = document.createElement('script');
    script.src = chatbotConfig.apiUrl + '/static/embed/chatbot.js';
    script.async = true;
    script.onload = function() {{
      GraphRAGChatbot.init(chatbotConfig);
    }};
    document.head.appendChild(script);
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = chatbotConfig.apiUrl + '/static/embed/chatbot.css';
    document.head.appendChild(link);
  }})();
</script>
"""
    
    return ChatbotSettingsResponse(
        workspace_id=workspace_id,
        settings=settings,
        embed_code=embed_code,
        updated_at=datetime.utcnow()
    )


@router.put("/{workspace_id}/settings", response_model=ChatbotSettingsResponse)
async def update_chatbot_settings(
    workspace_id: str,
    settings: ChatbotSettings,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Update chatbot widget settings"""
    
    # Verify access (owner only)
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can update chatbot settings"
        )
    
    # Update or create settings
    update_query = """
    MATCH (w:Workspace {id: $workspace_id})
    MERGE (w)-[:HAS_CHATBOT_SETTINGS]->(s:ChatbotSettings)
    SET s.title = $title,
        s.primary_color = $primary_color,
        s.position = $position,
        s.greeting_message = $greeting_message,
        s.placeholder_text = $placeholder_text,
        s.max_depth = $max_depth,
        s.top_k = $top_k,
        s.updated_at = datetime()
    RETURN s
    """
    
    await neo4j.execute_query(update_query, {
        "workspace_id": workspace_id,
        "title": settings.title,
        "primary_color": settings.primary_color,
        "position": settings.position,
        "greeting_message": settings.greeting_message,
        "placeholder_text": settings.placeholder_text,
        "max_depth": settings.max_depth,
        "top_k": settings.top_k
    })
    
    # Generate embed code
    embed_code = f"""
<!-- GraphRAG Chatbot Widget -->
<script>
  (function() {{
    var chatbotConfig = {{
      workspaceId: '{workspace_id}',
      apiKey: 'YOUR_API_KEY',
      apiUrl: 'http://localhost:8000'
    }};
    var script = document.createElement('script');
    script.src = chatbotConfig.apiUrl + '/static/embed/chatbot.js';
    script.async = true;
    script.onload = function() {{
      GraphRAGChatbot.init(chatbotConfig);
    }};
    document.head.appendChild(script);
  }})();
</script>
"""
    
    return ChatbotSettingsResponse(
        workspace_id=workspace_id,
        settings=settings,
        embed_code=embed_code,
        updated_at=datetime.utcnow()
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_api_key(
    chat_message: ChatMessage,
    neo4j: Neo4jService = Depends(get_neo4j_service),
    graphrag: GraphRAGService = Depends(get_graphrag_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Chat endpoint for embedded widgets (uses API key auth)"""
    
    # Verify API key
    workspace_info = await workspace_service.verify_api_key(chat_message.api_key)
    
    if not workspace_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    if workspace_info["workspace_id"] != chat_message.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match workspace"
        )
    
    # Check workspace limits
    limits_check = await workspace_service.check_workspace_limits(chat_message.workspace_id)
    
    if not limits_check["within_limits"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Workspace limits exceeded. Please upgrade your plan."
        )
    
    # Get chatbot settings for this workspace
    settings_query = """
    MATCH (w:Workspace {id: $workspace_id})-[:HAS_CHATBOT_SETTINGS]->(s:ChatbotSettings)
    RETURN s.max_depth as max_depth, s.top_k as top_k
    """
    
    settings_result = await neo4j.execute_query(settings_query, {
        "workspace_id": chat_message.workspace_id
    })
    
    max_depth = 2
    top_k = 10
    
    if settings_result:
        max_depth = settings_result[0].get("max_depth", 2)
        top_k = settings_result[0].get("top_k", 10)
    
    # Process query using GraphRAG
    # Limit query length to prevent memory issues
    limited_query = chat_message.message[:2000] if len(chat_message.message) > 2000 else chat_message.message
    
    # Limit depth and top_k to prevent memory overflow
    safe_max_depth = min(max_depth, 2)
    safe_top_k = min(top_k, 15)
    
    # Call graphrag.query with individual parameters (not QueryRequest object)
    response = await graphrag.query(
        user_query=limited_query,
        max_depth=safe_max_depth,
        top_k=safe_top_k,
        workspace_id=chat_message.workspace_id
    )
    
    # Handle response as dict (graphrag.query returns dict)
    if isinstance(response, dict):
        answer = response.get("answer", "")
        sources = response.get("sources", [])
    else:
        answer = response.answer
        sources = response.sources
    
    # Truncate answer if too long
    if len(answer) > 5000:
        answer = answer[:5000] + "..."
    
    return ChatResponse(
        message=chat_message.message,
        answer=answer,
        sources=sources[:5] if sources else [],  # Limit sources
        timestamp=datetime.utcnow()
    )


@router.get("/widget.js", response_class=HTMLResponse)
async def get_chatbot_widget_script():
    """Serve the chatbot widget JavaScript"""
    
    # This is a placeholder - in production, serve from static files
    script = """
// GraphRAG Chatbot Widget
(function() {
  'use strict';
  
  window.GraphRAGChatbot = {
    init: function(config) {
      // Create chatbot UI
      // Handle chat interactions
      // Call API endpoints
      console.log('GraphRAG Chatbot initialized', config);
    }
  };
})();
"""
    
    return script
