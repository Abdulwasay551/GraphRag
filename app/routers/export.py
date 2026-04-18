"""Export router for graph data"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import json
import csv
import io
import os
import tempfile

from app.models.schemas import (
    ExportRequest, ExportResponse, ExportFormat, TokenData
)
from app.utils.auth import get_current_user
from app.services.neo4j_service import Neo4jService

router = APIRouter(prefix="/api/export", tags=["Export"])


def get_neo4j_service() -> Neo4jService:
    """Dependency to get Neo4j service instance"""
    from app.main import neo4j_service
    return neo4j_service


@router.post("/{workspace_id}", response_model=ExportResponse)
async def export_graph(
    workspace_id: str,
    export_request: ExportRequest,
    current_user: TokenData = Depends(get_current_user),
    neo4j: Neo4jService = Depends(get_neo4j_service)
):
    """Export graph data in various formats"""
    
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
    
    export_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=24)
    
    # Build query based on filters
    where_clauses = ["(n)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})"]
    params = {"workspace_id": workspace_id}
    
    if export_request.include_labels:
        label_conditions = " OR ".join([f"n:{label}" for label in export_request.include_labels])
        where_clauses.append(f"({label_conditions})")
    
    where_clause = " AND ".join(where_clauses)
    limit_clause = f"LIMIT {export_request.max_nodes}" if export_request.max_nodes else ""
    
    # Get nodes
    nodes_query = f"""
    MATCH (n)
    WHERE {where_clause}
    RETURN n
    {limit_clause}
    """
    
    node_results = await neo4j.execute_query(nodes_query, params)
    
    # Get relationships
    rel_where = []
    if export_request.include_relationship_types:
        rel_where = [f"type(r) = '{t}'" for t in export_request.include_relationship_types]
        rel_condition = f"AND ({' OR '.join(rel_where)})" if rel_where else ""
    else:
        rel_condition = ""
    
    rels_query = f"""
    MATCH (source)-[r]->(target)
    WHERE (source)-[:IN_WORKSPACE]->(w:Workspace {{id: $workspace_id}})
    AND (target)-[:IN_WORKSPACE]->(w)
    {rel_condition}
    RETURN source, r, target
    """
    
    rel_results = await neo4j.execute_query(rels_query, params)
    
    # Generate export based on format
    export_dir = os.path.join(tempfile.gettempdir(), "graphrag_exports")
    os.makedirs(export_dir, exist_ok=True)
    
    if export_request.format == ExportFormat.JSON:
        filename = f"{export_id}.json"
        filepath = os.path.join(export_dir, filename)
        
        nodes = []
        for record in node_results:
            node = record["n"]
            nodes.append({
                "id": node.element_id,
                "labels": list(node.labels),
                "properties": dict(node)
            })
        
        relationships = []
        for record in rel_results:
            rel = record["r"]
            relationships.append({
                "source": record["source"].element_id,
                "target": record["target"].element_id,
                "type": rel.type,
                "properties": dict(rel)
            })
        
        with open(filepath, 'w') as f:
            json.dump({"nodes": nodes, "relationships": relationships}, f, indent=2, default=str)
    
    elif export_request.format == ExportFormat.CSV:
        filename = f"{export_id}_nodes.csv"
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "labels", "properties"])
            
            for record in node_results:
                node = record["n"]
                writer.writerow([
                    node.element_id,
                    ",".join(node.labels),
                    json.dumps(dict(node), default=str)
                ])
    
    elif export_request.format == ExportFormat.GRAPHML:
        filename = f"{export_id}.graphml"
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
            f.write('  <graph id="G" edgedefault="directed">\n')
            
            # Write nodes
            for record in node_results:
                node = record["n"]
                f.write(f'    <node id="{node.element_id}">\n')
                for key, value in dict(node).items():
                    f.write(f'      <data key="{key}">{value}</data>\n')
                f.write('    </node>\n')
            
            # Write edges
            for record in rel_results:
                source = record["source"]
                target = record["target"]
                rel = record["r"]
                f.write(f'    <edge source="{source.element_id}" target="{target.element_id}" label="{rel.type}"/>\n')
            
            f.write('  </graph>\n')
            f.write('</graphml>\n')
    
    elif export_request.format == ExportFormat.CYPHER:
        filename = f"{export_id}.cypher"
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w') as f:
            # Write CREATE statements for nodes
            for record in node_results:
                node = record["n"]
                labels = ":".join(node.labels)
                props = json.dumps(dict(node), default=str)
                f.write(f"CREATE (n:{labels} {props});\n")
            
            # Write CREATE statements for relationships
            for record in rel_results:
                source = record["source"]
                target = record["target"]
                rel = record["r"]
                rel_props = json.dumps(dict(rel), default=str) if dict(rel) else "{}"
                f.write(f"MATCH (a), (b) WHERE a.id = '{dict(source).get('id')}' AND b.id = '{dict(target).get('id')}' ")
                f.write(f"CREATE (a)-[:{rel.type} {rel_props}]->(b);\n")
    
    download_url = f"/api/export/download/{export_id}/{filename}"
    
    return ExportResponse(
        export_id=export_id,
        format=export_request.format,
        download_url=download_url,
        created_at=created_at,
        expires_at=expires_at
    )


@router.get("/download/{export_id}/{filename}")
async def download_export(
    export_id: str,
    filename: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Download exported file"""
    
    export_dir = os.path.join(tempfile.gettempdir(), "graphrag_exports")
    filepath = os.path.join(export_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found or expired"
        )
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )
