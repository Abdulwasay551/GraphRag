"""Authentication router"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.models.schemas import (
    UserCreate, UserLogin, UserResponse, Token, TokenData,
    WorkspaceCreate, WorkspaceResponse, WorkspacePlan
)
from app.utils.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
from app.services.neo4j_service import Neo4jService
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def convert_neo4j_datetime(dt):
    """Convert Neo4j DateTime to Python datetime"""
    if dt is None:
        return None
    if hasattr(dt, 'to_native'):
        return dt.to_native()
    return dt


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Register a new user and create default workspace"""
    
    # Check if user already exists
    check_query = """
    MATCH (u:User {email: $email})
    RETURN u
    """
    result = await neo4j.execute_query(check_query, {"email": user_data.email})
    
    if result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    created_at = datetime.utcnow()
    
    create_user_query = """
    CREATE (u:User {
        id: $user_id,
        email: $email,
        password_hash: $password_hash,
        full_name: $full_name,
        created_at: datetime($created_at),
        is_active: true
    })
    RETURN u
    """
    
    await neo4j.execute_query(create_user_query, {
        "user_id": user_id,
        "email": user_data.email,
        "password_hash": hashed_password,
        "full_name": user_data.full_name,
        "created_at": created_at.isoformat()
    })
    
    # Create default workspace
    workspace_id = str(uuid.uuid4())
    workspace_name = f"{user_data.full_name}'s Workspace"
    
    create_workspace_query = """
    MATCH (u:User {id: $user_id})
    CREATE (w:Workspace {
        id: $workspace_id,
        name: $workspace_name,
        description: 'Default workspace',
        plan: $plan,
        created_at: datetime($created_at)
    })
    CREATE (u)-[:OWNS {role: 'owner', added_at: datetime($created_at)}]->(w)
    RETURN w
    """
    
    await neo4j.execute_query(create_workspace_query, {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "plan": WorkspacePlan.FREE,
        "created_at": created_at.isoformat()
    })
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user_id, "email": user_data.email}
    )
    
    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        created_at=created_at,
        is_active=True
    )
    
    return Token(access_token=access_token, user=user_response)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Login with email and password"""
    
    # Find user
    query = """
    MATCH (u:User {email: $email})
    RETURN u
    """
    result = await neo4j.execute_query(query, {"email": credentials.email})
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user = result[0]["u"]
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user["id"], "email": user["email"]}
    )
    
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=convert_neo4j_datetime(user["created_at"]),
        is_active=user.get("is_active", True)
    )
    
    return Token(access_token=access_token, user=user_response)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get current user profile"""
    
    query = """
    MATCH (u:User {id: $user_id})
    RETURN u
    """
    result = await neo4j.execute_query(query, {"user_id": current_user.user_id})
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = result[0]["u"]
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=convert_neo4j_datetime(user["created_at"]),
        is_active=user.get("is_active", True)
    )


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def get_workspaces(
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get all workspaces for current user"""
    
    query = """
    MATCH (u:User {id: $user_id})-[r:OWNS|MEMBER_OF]->(w:Workspace)
    OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-(n)
    WITH w, r, count(DISTINCT n) as node_count
    OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-()-[rel]->()
    RETURN w, r.role as role, node_count, count(DISTINCT rel) as rel_count
    ORDER BY w.created_at DESC
    """
    
    results = await neo4j.execute_query(query, {"user_id": current_user.user_id})
    
    workspaces = []
    for record in results:
        w = record["w"]
        workspaces.append(WorkspaceResponse(
            id=w["id"],
            name=w["name"],
            description=w.get("description"),
            owner_id=current_user.user_id,  # Simplified for now
            plan=WorkspacePlan(w.get("plan", "free")),
            created_at=convert_neo4j_datetime(w["created_at"]),
            node_count=record.get("node_count", 0),
            relationship_count=record.get("rel_count", 0)
        ))
    
    return workspaces


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Get a specific workspace by ID"""
    
    query = """
    MATCH (u:User {id: $user_id})-[r:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-(n)
    WITH w, r, count(DISTINCT n) as node_count
    OPTIONAL MATCH (w)<-[:IN_WORKSPACE]-()-[rel]->()
    RETURN w, r.role as role, node_count, count(DISTINCT rel) as rel_count
    """
    
    results = await neo4j.execute_query(query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id
    })
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    record = results[0]
    w = record["w"]
    
    return WorkspaceResponse(
        id=w["id"],
        name=w["name"],
        description=w.get("description"),
        owner_id=current_user.user_id,
        plan=WorkspacePlan(w.get("plan", "free")),
        created_at=convert_neo4j_datetime(w["created_at"]),
        node_count=record.get("node_count", 0),
        relationship_count=record.get("rel_count", 0)
    )


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Create a new workspace"""
    
    workspace_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    query = """
    MATCH (u:User {id: $user_id})
    CREATE (w:Workspace {
        id: $workspace_id,
        name: $name,
        description: $description,
        plan: $plan,
        created_at: datetime($created_at)
    })
    CREATE (u)-[:OWNS {role: 'owner', added_at: datetime($created_at)}]->(w)
    RETURN w
    """
    
    result = await neo4j.execute_query(query, {
        "user_id": current_user.user_id,
        "workspace_id": workspace_id,
        "name": workspace_data.name,
        "description": workspace_data.description,
        "plan": WorkspacePlan.FREE,
        "created_at": created_at.isoformat()
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )
    
    w = result[0]["w"]
    
    return WorkspaceResponse(
        id=w["id"],
        name=w["name"],
        description=w.get("description"),
        owner_id=current_user.user_id,
        plan=WorkspacePlan(w.get("plan", "free")),
        created_at=w["created_at"],
        node_count=0,
        relationship_count=0
    )


# ============================================================================
# API Key Management
# ============================================================================

@router.post("/workspaces/{workspace_id}/api-keys")
async def create_api_key(
    workspace_id: str,
    key_data: dict,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Create a new API key for workspace"""
    
    # Verify user has access to workspace
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
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
    
    # Generate API key
    import secrets
    key_id = str(uuid.uuid4())
    api_key = f"grag_{secrets.token_urlsafe(32)}"
    name = key_data.get("name", "API Key")
    
    # Store API key
    create_key_query = """
    MATCH (w:Workspace {id: $workspace_id})
    CREATE (k:APIKey {
        id: $key_id,
        key: $api_key,
        name: $name,
        workspace_id: $workspace_id,
        created_at: datetime(),
        last_used: null,
        is_active: true
    })
    CREATE (w)-[:HAS_API_KEY]->(k)
    RETURN k
    """
    
    await neo4j.execute_query(create_key_query, {
        "workspace_id": workspace_id,
        "key_id": key_id,
        "api_key": api_key,
        "name": name
    })
    
    return {
        "id": key_id,
        "key": api_key,
        "name": name,
        "workspace_id": workspace_id,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True
    }


@router.get("/workspaces/{workspace_id}/api-keys")
async def list_api_keys(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """List all API keys for workspace"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
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
    
    # Get API keys
    keys_query = """
    MATCH (w:Workspace {id: $workspace_id})-[:HAS_API_KEY]->(k:APIKey)
    WHERE k.is_active = true
    RETURN k
    ORDER BY k.created_at DESC
    """
    
    keys_result = await neo4j.execute_query(keys_query, {"workspace_id": workspace_id})
    
    api_keys = []
    for record in keys_result:
        k = record["k"]
        api_keys.append({
            "id": k["id"],
            "key": k["key"],  # In production, mask this
            "name": k["name"],
            "workspace_id": k["workspace_id"],
            "created_at": convert_neo4j_datetime(k["created_at"]),
            "last_used": convert_neo4j_datetime(k.get("last_used")),
            "is_active": k["is_active"]
        })
    
    return {"api_keys": api_keys}


@router.delete("/workspaces/{workspace_id}/api-keys/{key_id}")
async def delete_api_key(
    workspace_id: str,
    key_id: str,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Delete an API key"""
    
    # Verify access
    access_query = """
    MATCH (u:User {id: $user_id})-[:OWNS|MEMBER_OF]->(w:Workspace {id: $workspace_id})
    RETURN w
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
    
    # Delete API key (soft delete)
    delete_query = """
    MATCH (w:Workspace {id: $workspace_id})-[:HAS_API_KEY]->(k:APIKey {id: $key_id})
    SET k.is_active = false
    RETURN k
    """
    
    delete_result = await neo4j.execute_query(delete_query, {
        "workspace_id": workspace_id,
        "key_id": key_id
    })
    
    if not delete_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"status": "success", "message": "API key deleted"}
