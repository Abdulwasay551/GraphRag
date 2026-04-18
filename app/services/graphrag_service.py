"""Core GraphRAG service implementing the RAG pipeline with graph context"""
from typing import List, Dict, Any, Optional
import logging
import uuid
import asyncio
import gc
from .neo4j_service import Neo4jService
from .ollama_service import OllamaService
from app.config import settings

logger = logging.getLogger(__name__)


class GraphRAGService:
    """GraphRAG service combining Neo4j graph database with LLM"""
    
    def __init__(self, neo4j_service: Neo4jService, ollama_service: OllamaService):
        """Initialize GraphRAG service"""
        self.neo4j = neo4j_service
        self.ollama = ollama_service
    
    async def query(
        self, 
        user_query: str, 
        max_depth: int = 2, 
        top_k: int = 10,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main GraphRAG query pipeline:
        1. Generate query embedding
        2. Find relevant nodes via similarity search
        3. Expand to neighboring nodes (graph context)
        4. Format context for LLM
        5. Generate answer with LLM
        """
        
        try:
            # Force garbage collection before processing
            gc.collect()
            
            # Limit inputs to prevent memory issues
            if len(user_query) > 10000:
                user_query = user_query[:10000]
            max_depth = min(max_depth, 2)
            top_k = min(top_k, 20)
            
            logger.info(f"Processing GraphRAG query: {user_query}")
            
            # NO OLLAMA MODE - Only keyword search (no embeddings)
            logger.info("Using keyword search only (embeddings disabled)...")
            relevant_nodes = await self.neo4j.keyword_search(
                user_query,
                limit=top_k,
                workspace_id=workspace_id
            )
            
            if relevant_nodes:
                logger.info(f"Found {len(relevant_nodes)} nodes via keyword search")
            
            if not relevant_nodes:
                logger.info("No relevant nodes found")
                # Get a sample of what IS in the database to help user
                sample_text = await self._get_sample_content()
                suggestion = "I couldn't find any relevant information in the knowledge graph to answer your question."
                if sample_text:
                    suggestion += f"\n\nYour documents contain data about: {sample_text}\n\nTry asking about these topics instead!"
                return self._empty_response(user_query, suggestion)
            
            # Step 2: Expand to neighboring nodes for richer context
            logger.debug("Expanding graph context...")
            all_nodes = []
            all_relationships = []
            seen_node_ids = set()
            
            for node in relevant_nodes:
                node_id = node.get("id")
                if not node_id:
                    continue
                
                # Add the node itself
                if node_id not in seen_node_ids:
                    all_nodes.append({
                        "id": node_id,
                        "labels": node.get("labels", []),
                        "properties": node.get("properties", {}),
                        "score": node.get("score")
                    })
                    seen_node_ids.add(node_id)
                
                # Get neighbors
                if max_depth > 0:
                    neighbors_data = await self.neo4j.get_neighbors(node_id, depth=max_depth)
                    
                    # Add neighboring nodes
                    for neighbor in neighbors_data.get("neighbors", []):
                        neighbor_id = neighbor.get("id")
                        if neighbor_id and neighbor_id not in seen_node_ids:
                            all_nodes.append(neighbor)
                            seen_node_ids.add(neighbor_id)
                    
                    # Add relationships
                    all_relationships.extend(neighbors_data.get("relationships", []))
            
            # Remove duplicate relationships
            unique_rels = []
            seen_rels = set()
            for rel in all_relationships:
                rel_key = (rel.get("source"), rel.get("target"), rel.get("type"))
                if rel_key not in seen_rels:
                    unique_rels.append(rel)
                    seen_rels.add(rel_key)
            
            logger.info(f"Expanded to {len(all_nodes)} nodes and {len(unique_rels)} relationships")
            
            # Step 3: Generate answer with Ollama LLM
            logger.info("Generating answer with Ollama LLM...")
            
            # Build context from found nodes (limit to prevent memory issues)
            context_parts = []
            for i, node in enumerate(all_nodes[:5], 1):  # Only top 5 nodes
                props = node.get("properties", {})
                text = props.get("text", props.get("name", props.get("title", "")))
                if text:
                    # For structured data, extract multiple rows for better analysis
                    if "Row 1:" in text and "Row 2:" in text:
                        # Include up to 3 rows for comparison
                        row3_idx = text.find("Row 3:")
                        if row3_idx != -1:
                            text = text[:row3_idx + 800]  # 3 rows worth
                        else:
                            text = text[:2000]  # 2 rows worth
                    else:
                        text = text[:1500]  # Regular content
                    
                    context_parts.append(text)
            
            context = "\n\n---\n\n".join(context_parts)
            
            # Create improved prompt for LLM with clear instructions
            prompt = f"""You are a helpful AI assistant analyzing data from a knowledge graph.

User Question: {user_query}

Data Available:
{context}

Instructions:
- Analyze the data carefully and answer the user's question directly
- If comparing items (like "best creator"), compare the actual metrics and give a specific recommendation
- Use natural, conversational language - no SQL queries or technical instructions
- Focus on the actual data values (followers, engagement rates, sales, etc.)
- If the data contains rows with metrics, compare them and identify the best option
- Keep your answer concise (2-3 paragraphs maximum)

Answer:"""
            
            # Generate answer with Ollama (with memory safety)
            try:
                answer = await self.ollama.generate(prompt, max_tokens=500)
                logger.info("LLM answer generated successfully")
            except Exception as e:
                logger.error(f"LLM generation failed: {e}, falling back to context only")
                # Fallback: return formatted context
                answer = f"Found {len(all_nodes)} relevant items:\n\n" + "\n\n".join(context_parts)
            
            # Cleanup prompt to free memory
            del prompt
            del context
            del context_parts
            gc.collect()
            
            # Format nodes for schema (convert labels array to single label string)
            formatted_nodes = []
            for node in all_nodes[:15]:  # Reduced limit for memory
                labels = node.get("labels", [])
                props = node.get("properties", {})
                # Only include essential properties to reduce memory
                safe_props = {
                    k: str(v)[:500] if isinstance(v, str) else v
                    for k, v in props.items()
                    if k in ["text", "name", "title", "description", "type"]
                }
                formatted_nodes.append({
                    "id": node.get("id"),
                    "label": labels[0] if labels else "Unknown",
                    "properties": safe_props,
                    "score": node.get("score")
                })
            
            # Format relationships (filter out invalid ones)
            formatted_rels = []
            for rel in unique_rels[:30]:  # Reduced from 50
                source = rel.get("source")
                target = rel.get("target")
                rel_type = rel.get("type")
                if source and target and rel_type:  # Skip if any required field is None
                    formatted_rels.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "properties": {}  # Omit relationship properties to save memory
                    })
            
            # Clear large variables before creating response
            del all_nodes
            del all_relationships
            del unique_rels
            gc.collect()
            
            # Prepare response
            return {
                "query": user_query,
                "answer": answer,
                "context_nodes": formatted_nodes,
                "relationships": formatted_rels,
                "sources": [node["id"] for node in relevant_nodes[:5]]
            }
            
        except Exception as e:
            logger.error(f"GraphRAG query error: {e}")
            gc.collect()  # Clean up on error
            return self._empty_response(
                user_query,
                f"An error occurred while processing your query: {str(e)}"
            )
        finally:
            # Always force garbage collection after query
            gc.collect()
    
    async def _get_sample_content(self) -> str:
        """Get a sample of what's actually in the database to help users"""
        try:
            # Get first DocumentChunk to show what data exists
            results = await self.neo4j.execute_query("""
                MATCH (c:DocumentChunk)
                RETURN c.text as text
                LIMIT 1
            """)
            
            if results:
                text = results[0].get("text", "")
                # Extract meaningful keywords from the content
                if "Row 1:" in text:
                    # CSV/Excel data - extract column names
                    cols_start = text.find("Columns:")
                    if cols_start != -1:
                        cols_end = text.find("\\n", cols_start)
                        if cols_end == -1:
                            cols_end = cols_start + 200
                        columns = text[cols_start:cols_end].replace("Columns:", "").strip()
                        # Get first few column names
                        col_list = [c.strip() for c in columns.split(",")[:5]]
                        return ", ".join(col_list)
                
                # Generic text - extract first meaningful words
                words = [w for w in text.split()[:50] if len(w) > 3]
                return " ".join(words[:20]) if words else "your uploaded documents"
            
            return "your uploaded documents"
        except Exception as e:
            logger.debug(f"Could not get sample content: {e}")
            return "your uploaded documents"
    
    def _empty_response(self, query: str, answer: str) -> Dict[str, Any]:
        """Create empty response"""
        return {
            "query": query,
            "answer": answer,
            "context_nodes": [],
            "relationships": [],
            "sources": []
        }
    
    async def ingest_document(
        self, 
        content: str, 
        metadata: Dict[str, Any],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        file_type: str = "text"  # NEW: file type to determine processing
    ) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge graph:
        1. Chunk the document
        2. Store chunks (with or without embeddings based on file type)
        3. Store in Neo4j
        
        File type handling:
        - csv, xlsx, xls: NO embeddings (already structured)
        - txt, md, json: NO embeddings by default (simple text storage)
        - pdf, docx: Can use embeddings if enabled in config
        """
        
        try:
            logger.info(f"Ingesting document: {metadata.get('title', 'Untitled')} (type: {file_type})")
            
            # Determine if this file type needs embeddings
            structured_types = ['csv', 'xlsx', 'xls', 'json']  # Never use embeddings
            simple_types = ['txt', 'md']  # Don't use embeddings by default
            
            use_embeddings = False  # Default: NO embeddings (safe mode)
            
            if file_type not in structured_types and file_type not in simple_types:
                # PDF, DOCX etc - can use embeddings if enabled in config
                use_embeddings = settings.enable_embeddings
            
            logger.info(f"File type '{file_type}' - Embeddings: {'ENABLED' if use_embeddings else 'DISABLED'}")
            
            # CRITICAL: Adjust content limits based on file type
            logger.info(f"Determining content limits for file type: {file_type}")
            
            # CSV/Excel: Parse and create graph structure
            if file_type in structured_types:
                logger.info(f"Structured file ({file_type}) - Will create graph from rows")
                max_content_size = 50_000  # 50KB for CSV/Excel
            elif file_type in simple_types:
                # Text files - simple storage
                max_content_size = 10_000  # Reduced from 50KB
            else:
                # PDF/DOCX - more conservative if embeddings enabled
                max_content_size = 2_000 if use_embeddings else 5_000  # Drastically reduced
            
            logger.info(f"Max content size: {max_content_size}, Current content: {len(content)} chars")
            if len(content) > max_content_size:
                logger.warning(f"Content truncated from {len(content)} to {max_content_size} chars")
                content = content[:max_content_size]
            
            # Use ultra-small chunks
            chunk_size = min(chunk_size, 200)  # Small chunks
            chunk_overlap = 10  # Minimal overlap
            
            logger.info(f"Starting text chunking with chunk_size={chunk_size}, overlap={chunk_overlap}")
            
            # For CSV/Excel: Create nodes from parsed rows instead of chunking
            if file_type in structured_types:
                logger.info(f"CSV/Excel detected - Creating graph nodes from rows")
                chunks = [content]  # Process as single chunk
                max_chunks = 1
            else:
                # Chunk the document
                chunks = self._chunk_text(content, chunk_size, chunk_overlap)
                logger.info(f"Created {len(chunks)} chunks")
                
                # EMERGENCY MODE: Only 2 chunks for all non-structured files
                max_chunks = 2
            
            if len(chunks) > max_chunks:
                logger.warning(f"EMERGENCY: Limiting chunks from {len(chunks)} to {max_chunks}")
                chunks = chunks[:max_chunks]
            
            nodes_created = 0
            relationships_created = 0
            
            # Import psutil for memory monitoring
            import psutil
            
            # EMERGENCY: STRICT SEQUENTIAL PROCESSING - ONE CHUNK AT A TIME
            logger.info(f"Processing {len(chunks)} chunks SEQUENTIALLY (one at a time)")
            
            for chunk_idx in range(len(chunks)):
                # CRITICAL: Emergency memory check with KILL switch
                mem = psutil.virtual_memory()
                logger.info(f"[Chunk {chunk_idx+1}/{len(chunks)}] Memory: {mem.percent:.1f}%")
                
                if mem.percent > 60:  # Kill very early - 60% threshold (was 65%)
                    logger.error(f"EMERGENCY STOP: Memory at {mem.percent}%, aborting NOW")
                    # Force emergency cleanup
                    del chunks
                    del content
                    gc.collect()
                    raise MemoryError(f"Emergency stop at {mem.percent}% memory")
                
                # EMERGENCY: Add delay between chunks to allow GC
                if chunk_idx > 0:
                    await asyncio.sleep(0.5)  # 500ms delay between chunks
                    gc.collect()  # Force GC between every chunk
                
                chunk_text = chunks[chunk_idx]
                
                # Truncate chunk (more generous for structured files)
                max_chunk_size = 10000 if file_type in ['csv', 'xlsx', 'xls', 'json'] else 1000
                if len(chunk_text) > max_chunk_size:
                    chunk_text = chunk_text[:max_chunk_size]
                
                chunk_id = metadata.get("document_id", str(uuid.uuid4())) + f"_chunk_{chunk_idx}"
                
                try:
                    # Smart embedding logic based on file type
                    if use_embeddings:
                        logger.info(f"[Chunk {chunk_idx+1}/{len(chunks)}] Generating embedding...")
                        try:
                            embedding = await self.ollama.embeddings(chunk_text)
                        except Exception as e:
                            logger.warning(f"Embedding failed: {e}, continuing without")
                            embedding = []
                    else:
                        # Structured/simple files - NO Ollama
                        logger.info(f"[Chunk {chunk_idx+1}/{len(chunks)}] Storing text only (no embeddings for {file_type})...")
                        embedding = []
                    
                    # Prepare and insert immediately (NO EMBEDDINGS)
                    chunk_properties = {
                        "id": chunk_id,
                        "text": chunk_text,  # Store full text for keyword search
                        "chunk_index": chunk_idx,
                        # No embedding field - saves space and avoids Ollama
                        **{k: v for k, v in metadata.items() if k not in ["id", "document_id"]}
                    }
                    
                    # Insert immediately
                    await self.neo4j.create_node("DocumentChunk", chunk_properties, merge_on="id")
                    nodes_created += 1
                    
                    # Update progress for live UI
                    if "document_id" in metadata:
                        try:
                            await self.neo4j.execute_query(
                                """
                                MATCH (d:Document {id: $document_id})
                                SET d.progress = $progress, 
                                    d.progress_message = $message,
                                    d.chunks_processed = $chunks_done
                                """,
                                {
                                    "document_id": metadata["document_id"],
                                    "progress": int((chunk_idx + 1) / len(chunks) * 100),
                                    "message": f"Processing chunk {chunk_idx+1} of {len(chunks)}",
                                    "chunks_done": chunk_idx + 1
                                }
                            )
                        except:
                            pass
                    
                    logger.info(f"[Chunk {chunk_idx+1}/{len(chunks)}] ✓ Complete")
                    
                    # CRITICAL: Immediate cleanup
                    del chunk_properties
                    del chunk_text
                    gc.collect()
                    
                    # CRITICAL: 5 second delay - give system time to recover
                    logger.info(f"[Chunk {chunk_idx+1}/{len(chunks)}] Waiting 5s for system recovery...")
                    await asyncio.sleep(5.0)
                    
                except Exception as e:
                    logger.error(f"[Chunk {chunk_idx+1}/{len(chunks)}] Failed: {e}")
                    continue
            
            logger.info(f"Ingestion complete: {nodes_created} nodes, {relationships_created} relationships")
            
            result = {
                "status": "success",
                "chunks_created": len(chunks),
                "nodes_created": nodes_created,
                "relationships_created": relationships_created,
                "message": f"Successfully ingested document with {nodes_created} nodes and {relationships_created} relationships"
            }
            
            # CRITICAL: Final aggressive cleanup
            del chunks
            del content
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Document ingestion error: {e}")
            # Cleanup on error too
            gc.collect()
            return {
                "status": "error",
                "chunks_created": 0,
                "nodes_created": 0,
                "relationships_created": 0,
                "message": f"Failed to ingest document: {str(e)}"
            }
        finally:
            # CRITICAL: Always cleanup after ingestion
            gc.collect()
            logger.info("Memory cleanup completed")
    
    def _chunk_text(
        self, 
        text: str, 
        chunk_size: int = 500, 
        overlap: int = 50
    ) -> List[str]:
        """Split text into overlapping chunks"""
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence end
                for delimiter in ['. ', '! ', '? ', '\n\n']:
                    pos = text.rfind(delimiter, start, end)
                    if pos != -1:
                        end = pos + len(delimiter)
                        break
                else:
                    # Look for word boundary
                    pos = text.rfind(' ', start, end)
                    if pos != -1:
                        end = pos
            
            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end
        
        return chunks
