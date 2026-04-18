"""Workspace service for multi-tenancy management"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.services.neo4j_service import Neo4jService
from app.models.schemas import WorkspacePlan


class WorkspaceService:
    """Service for managing workspaces and multi-tenancy"""
    
    def __init__(self, neo4j_service: Neo4jService):
        self.neo4j = neo4j_service
    
    async def get_workspace_limits(self, workspace_id: str) -> Dict[str, int]:
        """Get resource limits for a workspace based on its plan"""
        query = """
        MATCH (w:Workspace {id: $workspace_id})
        RETURN w.plan as plan
        """
        result = await self.neo4j.execute_query(query, {"workspace_id": workspace_id})
        
        if not result:
            return {"max_nodes": 1000, "max_relationships": 5000}
        
        plan = result[0].get("plan", "free")
        
        limits = {
            "free": {"max_nodes": 1000, "max_relationships": 5000},
            "pro": {"max_nodes": 50000, "max_relationships": 250000},
            "enterprise": {"max_nodes": -1, "max_relationships": -1}  # unlimited
        }
        
        return limits.get(plan, limits["free"])
    
    async def check_workspace_limits(self, workspace_id: str) -> Dict[str, Any]:
        """Check if workspace is within limits"""
        query = """
        MATCH (w:Workspace {id: $workspace_id})
        OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-(n)
        WITH w, count(DISTINCT n) as node_count
        OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-()-[r]->()
        RETURN w.plan as plan, node_count, count(DISTINCT r) as rel_count
        """
        
        result = await self.neo4j.execute_query(query, {"workspace_id": workspace_id})
        
        if not result:
            return {"within_limits": True, "message": "Workspace not found"}
        
        record = result[0]
        limits = await self.get_workspace_limits(workspace_id)
        
        node_count = record.get("node_count", 0)
        rel_count = record.get("rel_count", 0)
        
        max_nodes = limits["max_nodes"]
        max_rels = limits["max_relationships"]
        
        within_limits = True
        messages = []
        
        if max_nodes != -1 and node_count >= max_nodes:
            within_limits = False
            messages.append(f"Node limit reached ({node_count}/{max_nodes})")
        
        if max_rels != -1 and rel_count >= max_rels:
            within_limits = False
            messages.append(f"Relationship limit reached ({rel_count}/{max_rels})")
        
        return {
            "within_limits": within_limits,
            "node_count": node_count,
            "max_nodes": max_nodes,
            "relationship_count": rel_count,
            "max_relationships": max_rels,
            "messages": messages
        }
    
    async def create_api_key(self, workspace_id: str, name: str) -> Dict[str, Any]:
        """Create an API key for a workspace"""
        api_key_id = str(uuid.uuid4())
        api_key = f"grag_{uuid.uuid4().hex}"
        created_at = datetime.utcnow()
        
        query = """
        MATCH (w:Workspace {id: $workspace_id})
        CREATE (k:APIKey {
            id: $api_key_id,
            key: $api_key,
            name: $name,
            created_at: datetime($created_at),
            is_active: true
        })
        CREATE (k)-[:BELONGS_TO]->(w)
        RETURN k
        """
        
        result = await self.neo4j.execute_query(query, {
            "workspace_id": workspace_id,
            "api_key_id": api_key_id,
            "api_key": api_key,
            "name": name,
            "created_at": created_at.isoformat()
        })
        
        if result:
            return {
                "id": api_key_id,
                "key": api_key,
                "name": name,
                "created_at": created_at
            }
        
        return None
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify an API key and return workspace info"""
        query = """
        MATCH (w:Workspace)-[:HAS_API_KEY]->(k:APIKey {key: $api_key, is_active: true})
        SET k.last_used = datetime()
        RETURN w.id as workspace_id, w.plan as plan, w.name as workspace_name
        """
        
        result = await self.neo4j.execute_query(query, {"api_key": api_key})
        
        if result:
            return result[0]
        
        return None
    
    async def add_workspace_label_to_node(self, node_id: str, workspace_id: str) -> bool:
        """Add workspace label to a node for isolation"""
        query = """
        MATCH (n) WHERE elementId(n) = $node_id
        MATCH (w:Workspace {id: $workspace_id})
        CREATE (n)-[:IN_WORKSPACE]->(w)
        RETURN n
        """
        
        result = await self.neo4j.execute_query(query, {
            "node_id": node_id,
            "workspace_id": workspace_id
        })
        
        return len(result) > 0
