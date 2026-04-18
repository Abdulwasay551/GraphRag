"""Visualization router for graph exploration"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.models.schemas import GraphStats
from app.services.neo4j_service import Neo4jService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Visualization"])
templates = Jinja2Templates(directory="app/templates")


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page"""
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/workspace/{workspace_id}", response_class=HTMLResponse)
async def workspace_page(request: Request, workspace_id: str):
    """Workspace detail page"""
    return templates.TemplateResponse("workspace.html", {"request": request})


@router.get("/chatbot-settings", response_class=HTMLResponse)
async def chatbot_settings_page(request: Request):
    """Chatbot settings page"""
    return templates.TemplateResponse("chatbot_settings.html", {"request": request})


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Document upload page"""
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    """Documents page (alias for upload)"""
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get("/query", response_class=HTMLResponse)
async def query_page(request: Request):
    """Query interface page"""
    return templates.TemplateResponse("query.html", {"request": request})


@router.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    """Chatbot interface page"""
    return templates.TemplateResponse("chatbot.html", {"request": request})


@router.get("/schema", response_class=HTMLResponse)
async def schema_page(request: Request):
    """Schema visualization page"""
    return templates.TemplateResponse("schema.html", {"request": request})


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page"""
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Terms of Service page"""
    return templates.TemplateResponse("terms.html", {"request": request})


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    """Privacy Policy page"""
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    """Contact page"""
    return templates.TemplateResponse("contact.html", {"request": request})


@router.get("/graph-view", response_class=HTMLResponse)
async def graph_view(request: Request):
    """Legacy graph visualization page"""
    return templates.TemplateResponse(
        "graph_view.html",
        {
            "request": request,
            "answer": None,
            "context_nodes": [],
            "relationships": []
        }
    )


@router.get("/visualize/{node_id}", response_class=HTMLResponse)
async def visualize_node(
    request: Request,
    node_id: str,
    depth: int = 2,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Visualize a subgraph around a specific node"""
    try:
        subgraph = await service.get_subgraph(node_id, depth=depth)
        
        return templates.TemplateResponse(
            "graph_view.html",
            {
                "request": request,
                "center_node": subgraph.get("center"),
                "nodes": subgraph.get("nodes", []),
                "relationships": subgraph.get("relationships", []),
                "node_id": node_id
            }
        )
        
    except Exception as e:
        logger.error(f"Visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/graph/stats", response_model=GraphStats)
async def get_graph_stats(
    workspace_id: str = None,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Get knowledge graph statistics for a workspace"""
    try:
        if workspace_id:
            stats = await service.get_workspace_stats(workspace_id)
        else:
            stats = await service.get_graph_stats()
        return GraphStats(**stats)
        
    except Exception as e:
        logger.error(f"Stats endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ALIAS: Same endpoint under different path for workspace page
@router.get("/api/visualization/stats", response_model=GraphStats)
async def get_visualization_stats(
    workspace_id: str = None,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Get visualization statistics (alias for workspace compatibility)"""
    return await get_graph_stats(workspace_id, service)


@router.get("/api/visualization/graph")
async def get_visualization_graph(
    workspace_id: str = None,
    limit: int = 50,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Get graph data for visualization"""
    try:
        if workspace_id:
            # Get nodes and relationships for workspace
            query = """
            MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk)
            WITH collect(DISTINCT d) + collect(DISTINCT c) as allNodes
            UNWIND allNodes as n
            WITH n WHERE n.id IS NOT NULL
            WITH collect(DISTINCT {
                id: n.id,
                name: coalesce(n.filename, substring(n.text, 0, 50), n.name, 'Node'),
                label: head(labels(n))
            })[0..$limit] as nodeList
            WITH nodeList, [n IN nodeList | n.id] as nodeIds
            MATCH (source)-[r]-(target)
            WHERE source.id IN nodeIds AND target.id IN nodeIds
            RETURN 
                nodeList as nodes,
                collect(DISTINCT {
                    source: source.id,
                    target: target.id,
                    type: type(r)
                }) as edges
            """
            results = await service.execute_query(query, {
                "workspace_id": workspace_id,
                "limit": limit
            })
            
            if results:
                return {
                    "nodes": results[0].get("nodes", []),
                    "edges": results[0].get("edges", [])
                }
        
        return {"nodes": [], "edges": []}
        
    except Exception as e:
        logger.error(f"Visualization graph error: {e}")
        return {"nodes": [], "edges": []}


@router.get("/api/graph/node/{node_id}")
async def get_node(node_id: str, service: Neo4jService = Depends(get_neo4j_service)):
    """Get details for a specific node"""
    try:
        results = await service.search_nodes(property_filters={"id": node_id}, limit=1)
        
        if not results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return results[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/graph/neighbors/{node_id}")
async def get_neighbors(
    node_id: str,
    depth: int = 1,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Get neighboring nodes and relationships"""
    try:
        neighbors = await service.get_neighbors(node_id, depth=depth)
        return neighbors
        
    except Exception as e:
        logger.error(f"Get neighbors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/graph/search")
async def search_nodes(
    label: str = None,
    limit: int = 100,
    service: Neo4jService = Depends(get_neo4j_service)
):
    """Search nodes by label"""
    try:
        results = await service.search_nodes(label=label, limit=limit)
        return {"nodes": results}
        
    except Exception as e:
        logger.error(f"Search nodes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/graph/clear")
async def clear_database(service: Neo4jService = Depends(get_neo4j_service)):
    """Clear all nodes and relationships (use with caution!)"""
    try:
        await service.clear_database()
        return {"status": "success", "message": "Database cleared"}
        
    except Exception as e:
        logger.error(f"Clear database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
