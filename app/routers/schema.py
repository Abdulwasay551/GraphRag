"""Custom schema builder router"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
import uuid

from app.models.schemas import (
    EntityTypeCreate, RelationshipTypeCreate, WorkspaceSchema, TokenData
)
from app.utils.auth import get_current_user
from app.services.neo4j_service import Neo4jService

router = APIRouter(prefix="/api/schema", tags=["Schema Builder"])


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


@router.get("/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace_schema(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get custom schema for a workspace"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    access_result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not access_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    # Get entity types
    entity_query = """
    MATCH (w:Workspace {id: $workspace_id})<-[:DEFINED_IN]-(et:EntityType)
    RETURN et
    ORDER BY et.name
    """
    
    entity_results = await neo4j.execute_query(entity_query, {"workspace_id": workspace_id})
    
    entity_types = []
    for record in entity_results:
        et = record["et"]
        entity_types.append(EntityTypeCreate(
            name=et["name"],
            description=et.get("description"),
            color=et.get("color", "#3B82F6"),
            properties=et.get("properties", [])
        ))
    
    # Get relationship types
    rel_query = """
    MATCH (w:Workspace {id: $workspace_id})<-[:DEFINED_IN]-(rt:RelationshipType)
    RETURN rt
    ORDER BY rt.name
    """
    
    rel_results = await neo4j.execute_query(rel_query, {"workspace_id": workspace_id})
    
    relationship_types = []
    for record in rel_results:
        rt = record["rt"]
        relationship_types.append(RelationshipTypeCreate(
            name=rt["name"],
            description=rt.get("description"),
            source_entity_types=rt.get("source_entity_types", []),
            target_entity_types=rt.get("target_entity_types", [])
        ))
    
    return WorkspaceSchema(
        workspace_id=workspace_id,
        entity_types=entity_types,
        relationship_types=relationship_types,
        updated_at=datetime.utcnow()
    )


@router.post("/{workspace_id}/entity-types", response_model=EntityTypeCreate)
async def create_entity_type(
    workspace_id: str,
    entity_type: EntityTypeCreate,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Create a custom entity type"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    access_result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not access_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    # Check if entity type already exists
    check_query = """
    MATCH (w:Workspace {id: $workspace_id})<-[:DEFINED_IN]-(et:EntityType {name: $name})
    RETURN et
    """
    
    existing = await neo4j.execute_query(check_query, {
        "workspace_id": workspace_id,
        "name": entity_type.name
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entity type '{entity_type.name}' already exists"
        )
    
    # Create entity type
    create_query = """
    MATCH (w:Workspace {id: $workspace_id})
    CREATE (et:EntityType {
        id: $id,
        name: $name,
        description: $description,
        color: $color,
        properties: $properties,
        created_at: datetime()
    })
    CREATE (et)-[:DEFINED_IN]->(w)
    RETURN et
    """
    
    await neo4j.execute_query(create_query, {
        "workspace_id": workspace_id,
        "id": str(uuid.uuid4()),
        "name": entity_type.name,
        "description": entity_type.description,
        "color": entity_type.color,
        "properties": entity_type.properties
    })
    
    return entity_type


@router.post("/{workspace_id}/relationship-types", response_model=RelationshipTypeCreate)
async def create_relationship_type(
    workspace_id: str,
    relationship_type: RelationshipTypeCreate,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Create a custom relationship type"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    access_result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not access_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    # Create relationship type
    create_query = """
    MATCH (w:Workspace {id: $workspace_id})
    CREATE (rt:RelationshipType {
        id: $id,
        name: $name,
        description: $description,
        source_entity_types: $source_entity_types,
        target_entity_types: $target_entity_types,
        created_at: datetime()
    })
    CREATE (rt)-[:DEFINED_IN]->(w)
    RETURN rt
    """
    
    await neo4j.execute_query(create_query, {
        "workspace_id": workspace_id,
        "id": str(uuid.uuid4()),
        "name": relationship_type.name,
        "description": relationship_type.description,
        "source_entity_types": relationship_type.source_entity_types,
        "target_entity_types": relationship_type.target_entity_types
    })
    
    return relationship_type


@router.delete("/{workspace_id}/entity-types/{entity_type_name}")
async def delete_entity_type(
    workspace_id: str,
    entity_type_name: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Delete a custom entity type"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    access_result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not access_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can delete entity types"
        )
    
    # Delete entity type
    delete_query = """
    MATCH (w:Workspace {id: $workspace_id})<-[:DEFINED_IN]-(et:EntityType {name: $name})
    DETACH DELETE et
    """
    
    await neo4j.execute_query(delete_query, {
        "workspace_id": workspace_id,
        "name": entity_type_name
    })
    
    return {"status": "success", "message": f"Entity type '{entity_type_name}' deleted"}


@router.delete("/{workspace_id}/relationship-types/{relationship_type_name}")
async def delete_relationship_type(
    workspace_id: str,
    relationship_type_name: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Delete a custom relationship type"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(w:Workspace {id: $workspace_id})
    RETURN w
    """
    
    access_result = await neo4j.execute_query(access_query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not access_result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can delete relationship types"
        )
    
    # Delete relationship type
    delete_query = """
    MATCH (w:Workspace {id: $workspace_id})<-[:DEFINED_IN]-(rt:RelationshipType {name: $name})
    DETACH DELETE rt
    """
    
    await neo4j.execute_query(delete_query, {
        "workspace_id": workspace_id,
        "name": relationship_type_name
    })
    
    return {"status": "success", "message": f"Relationship type '{relationship_type_name}' deleted"}
