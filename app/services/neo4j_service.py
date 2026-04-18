"""Neo4j database service with async support"""
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Neo4jService:
    """Async Neo4j database service for GraphRAG operations"""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j connection"""
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = None
        
    async def connect(self):
        """Establish database connection with memory-optimized pool settings"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=10,  # Limit connections
                connection_acquisition_timeout=30,  # 30 second timeout
                max_transaction_retry_time=15,  # Reduce retry time
                fetch_size=100  # Limit fetch size to reduce memory
            )
            # Verify connection
            await self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results with memory limits"""
        if not self.driver:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        parameters = parameters or {}
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters)
            # Limit results to prevent memory overflow
            max_results = 1000
            records = []
            count = 0
            async for record in result:
                if count >= max_results:
                    logger.warning(f"Query returned more than {max_results} results, truncating")
                    break
                records.append(record.data())
                count += 1
            return records
    
    async def execute_write(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a write query (CREATE, MERGE, etc.)"""
        if not self.driver:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        parameters = parameters or {}
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters)
            records = [record.data() async for record in result]
            await session.close()
            return records
    
    async def semantic_search(
        self, 
        embedding: List[float], 
        limit: int = 10,
        node_label: str = "Document"
    ) -> List[Dict[str, Any]]:
        """Find nodes with similar embeddings using cosine similarity"""
        # Limit to prevent memory issues
        limit = min(limit, 50)
        
        query = f"""
        MATCH (n:{node_label})
        WHERE n.embedding IS NOT NULL
        WITH n, 
             reduce(dot = 0.0, i IN range(0, size(n.embedding)-1) | 
                    dot + n.embedding[i] * $embedding[i]) AS dotProduct,
             sqrt(reduce(norm1 = 0.0, i IN range(0, size(n.embedding)-1) | 
                    norm1 + n.embedding[i] * n.embedding[i])) AS norm1,
             sqrt(reduce(norm2 = 0.0, i IN range(0, size($embedding)-1) | 
                    norm2 + $embedding[i] * $embedding[i])) AS norm2
        WITH n, dotProduct / (norm1 * norm2) AS similarity
        WHERE similarity > 0.1
        RETURN n.id AS id, 
               labels(n) AS labels,
               properties(n) AS properties,
               similarity AS score
        ORDER BY similarity DESC
        LIMIT $limit
        """
        
        results = await self.execute_query(query, {
            "embedding": embedding,
            "limit": limit
        })
        
        return results
    
    async def keyword_search(
        self,
        query: str,
        limit: int = 10,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search for nodes when embeddings aren't available"""
        # Extract meaningful words from query (remove common stop words)
        stop_words = {'tell', 'me', 'about', 'what', 'who', 'when', 'where', 'why', 'how', 
                     'is', 'are', 'was', 'were', 'the', 'a', 'an', 'in', 'on', 'at', 'to',
                     'for', 'of', 'with', 'from', 'by', 'this', 'that', 'these', 'those',
                     'database', 'movies', 'do', 'you', 'know', 'can', 'please'}
        
        query_words = [w.lower() for w in query.split() if w.lower() not in stop_words and len(w) > 2]
        
        if not query_words:
            query_words = [query.lower()]  # Fallback to full query if all words filtered
        
        logger.info(f"Keyword search terms: {query_words}")
        
        # Search for ANY of the key terms
        workspace_filter = ""
        if workspace_id:
            workspace_filter = "AND (n)-[:IN_WORKSPACE]->(:Workspace {id: $workspace_id})"
        
        cypher_query = f"""
        CALL {{
            MATCH (n)
            WHERE any(term IN $terms WHERE 
                toLower(coalesce(n.name, n.title, n.text, '')) CONTAINS term
                OR toLower(coalesce(n.plot, n.description, n.bio, '')) CONTAINS term
            )
            {workspace_filter}
            RETURN n.id AS id,
                   labels(n) AS labels,
                   properties(n) AS properties,
                   1.0 AS score
            LIMIT $limit
            
            UNION
            
            MATCH (n)-[r]-(m)
            WHERE any(term IN $terms WHERE
                toLower(coalesce(m.name, m.title, m.text, '')) CONTAINS term
                OR toLower(type(r)) CONTAINS term
            )
            {workspace_filter}
            RETURN DISTINCT n.id AS id,
                   labels(n) AS labels,
                   properties(n) AS properties,
                   0.8 AS score
            LIMIT $limit
        }}
        RETURN id, labels, properties, score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        params = {
            "terms": query_words,
            "limit": limit
        }
        if workspace_id:
            params["workspace_id"] = workspace_id
        
        results = await self.execute_query(cypher_query, params)
        logger.info(f"Keyword search returned {len(results)} results")
        
        return results
    
    async def get_neighbors(
        self, 
        node_id: str, 
        depth: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get neighboring nodes and relationships up to specified depth"""
        
        # Limit depth to prevent exponential growth
        depth = min(depth, 2)
        
        rel_filter = ""
        if relationship_types:
            rel_filter = ":" + "|".join(relationship_types)
        
        # Build query with literal depth value (Neo4j doesn't support parameters in path patterns)
        query = f"""
        MATCH path = (start {{id: $node_id}})-[{rel_filter}*1..{depth}]-(neighbor)
        WITH start, neighbor, relationships(path) AS rels, nodes(path) AS nodes
        RETURN DISTINCT
            start.id AS start_id,
            collect(DISTINCT {{
                id: neighbor.id,
                labels: labels(neighbor),
                properties: properties(neighbor)
            }}) AS neighbors,
            collect(DISTINCT {{
                source: startNode(rels[0]).id,
                target: endNode(rels[0]).id,
                type: type(rels[0]),
                properties: properties(rels[0])
            }}) AS relationships
        """
        
        results = await self.execute_query(query, {
            "node_id": node_id
        })
        
        if not results:
            return {"neighbors": [], "relationships": []}
        
        return results[0] if results else {"neighbors": [], "relationships": []}
    
    async def get_subgraph(self, node_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get complete subgraph around a node"""
        # Build query with literal depth value
        query = f"""
        MATCH path = (center {{id: $node_id}})-[*0..{depth}]-(node)
        WITH center, collect(DISTINCT node) AS nodes, collect(DISTINCT path) AS paths
        UNWIND paths AS p
        WITH center, nodes,
             [rel IN relationships(p) | {{
                 source: startNode(rel).id,
                 target: endNode(rel).id,
                 type: type(rel),
                 properties: properties(rel)
             }}] AS rels
        RETURN 
            {{id: center.id, labels: labels(center), properties: properties(center)}} AS center_node,
            [n IN nodes | {{id: n.id, labels: labels(n), properties: properties(n)}}] AS all_nodes,
            reduce(allRels = [], r IN rels | allRels + r) AS all_relationships
        """
        
        results = await self.execute_query(query, {
            "node_id": node_id
        })
        
        if not results:
            return {"center": None, "nodes": [], "relationships": []}
        
        result = results[0]
        return {
            "center": result.get("center_node"),
            "nodes": result.get("all_nodes", []),
            "relationships": result.get("all_relationships", [])
        }
    
    async def create_node(
        self, 
        label: str, 
        properties: Dict[str, Any],
        merge_on: Optional[str] = "id"
    ) -> Dict[str, Any]:
        """Create or merge a node"""
        
        if merge_on and merge_on in properties:
            query = f"""
            MERGE (n:{label} {{{merge_on}: ${merge_on}}})
            SET n += $properties
            RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
            """
            params = {merge_on: properties[merge_on], "properties": properties}
        else:
            query = f"""
            CREATE (n:{label} $properties)
            RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
            """
            params = {"properties": properties}
        
        results = await self.execute_write(query, params)
        return results[0] if results else {}
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a relationship between two nodes"""
        
        properties = properties or {}
        
        query = f"""
        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $properties
        RETURN 
            source.id AS source,
            target.id AS target,
            type(r) AS type,
            properties(r) AS properties
        """
        
        results = await self.execute_write(query, {
            "source_id": source_id,
            "target_id": target_id,
            "properties": properties
        })
        
        return results[0] if results else {}
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        # Count nodes by label
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        """
        node_results = await self.execute_query(node_query)
        
        # Count relationships by type
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        """
        rel_results = await self.execute_query(rel_query)
        
        node_labels = {r["label"]: r["count"] for r in node_results if r["label"]}
        rel_types = {r["type"]: r["count"] for r in rel_results}
        
        return {
            "total_nodes": sum(node_labels.values()),
            "total_relationships": sum(rel_types.values()),
            "node_labels": node_labels,
            "relationship_types": rel_types
        }
    
    async def get_workspace_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Get statistics for a specific workspace"""
        
        # Count documents in workspace
        doc_query = """
        MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
        RETURN count(d) as document_count
        """
        doc_result = await self.execute_query(doc_query, {"workspace_id": workspace_id})
        documents = doc_result[0]["document_count"] if doc_result else 0
        
        # Count all nodes related to workspace (documents + chunks)
        node_query = """
        MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk)
        RETURN count(DISTINCT d) + count(DISTINCT c) as node_count
        """
        node_result = await self.execute_query(node_query, {"workspace_id": workspace_id})
        nodes = node_result[0]["node_count"] if node_result else 0
        
        # Count relationships
        rel_query = """
        MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
        OPTIONAL MATCH (d)-[r]-()
        RETURN count(r) as rel_count
        """
        rel_result = await self.execute_query(rel_query, {"workspace_id": workspace_id})
        relationships = rel_result[0]["rel_count"] if rel_result else 0
        
        # Get entity types (node labels)
        entity_query = """
        MATCH (d:Document)-[:IN_WORKSPACE]->(w:Workspace {id: $workspace_id})
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk)
        WITH collect(DISTINCT d) + collect(DISTINCT c) as allNodes
        UNWIND allNodes as n
        RETURN labels(n)[0] as label, count(*) as count
        """
        entity_result = await self.execute_query(entity_query, {"workspace_id": workspace_id})
        entity_types = [{"name": r["label"], "count": r["count"]} for r in entity_result if r["label"]]
        
        return {
            "nodes": nodes,
            "relationships": relationships,
            "documents": documents,
            "entity_types": entity_types,
            "total_nodes": nodes,
            "total_relationships": relationships,
            "node_labels": {et["name"]: et["count"] for et in entity_types},
            "relationship_types": {}
        }
    
    async def clear_database(self):
        """Clear all nodes and relationships (use with caution!)"""
        query = """
        MATCH (n)
        DETACH DELETE n
        """
        await self.execute_write(query)
        logger.warning("Database cleared")
    
    async def search_nodes(
        self,
        label: Optional[str] = None,
        property_filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search nodes by label and properties"""
        
        label_filter = f":{label}" if label else ""
        
        where_clauses = []
        params = {"limit": limit}
        
        if property_filters:
            for key, value in property_filters.items():
                param_name = f"prop_{key}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
        MATCH (n{label_filter})
        {where_clause}
        RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
        LIMIT $limit
        """
        
        return await self.execute_query(query, params)
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            if not self.driver:
                return False
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
