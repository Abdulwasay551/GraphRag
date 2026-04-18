"""Ollama LLM service for text generation and embeddings"""
import ollama
from typing import List, Dict, Any, Optional
import logging
import json
import asyncio

logger = logging.getLogger(__name__)


class OllamaService:
    """Async Ollama service for LLM operations"""
    
    def __init__(self, base_url: str, model: str = "llama3.2:1b", timeout: int = 120):
        """Initialize Ollama service"""
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.client = ollama.AsyncClient(host=base_url, timeout=timeout)
        
    async def close(self):
        """Close client (ollama client doesn't require explicit closing)"""
        pass
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text completion"""
        try:
            options = {
                "temperature": temperature
            }
            
            if max_tokens:
                options["num_predict"] = max_tokens
            
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                options=options,
                stream=False
            )
            
            return response.get("response", "")
            
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7
    ) -> str:
        """Chat completion with message history"""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": temperature},
                stream=False
            )
            
            return response.get("message", {}).get("content", "")
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text with memory cleanup"""
        try:
            # Truncate very long text to prevent memory issues
            max_text_length = 2000  # Limit input size
            if len(text) > max_text_length:
                text = text[:max_text_length]
            
            response = await self.client.embeddings(
                model=self.model,
                prompt=text
            )
            
            embedding = response.get("embedding", [])
            
            # Clear response immediately
            del response
            
            return embedding
            
        except Exception as e:
            logger.error(f"Ollama embeddings error: {e}")
            raise
    
    async def query_with_context(
        self, 
        query: str,
        context_nodes: List[Dict[str, Any]],
        context_relationships: List[Dict[str, Any]]
    ) -> str:
        """Query with graph context for GraphRAG"""
        
        # Format graph context for LLM
        context = self._format_graph_context(context_nodes, context_relationships)
        
        system_prompt = """You are a helpful AI assistant that answers questions based on a knowledge graph.
Use the provided graph context to answer questions accurately and concisely.
If the information needed to answer the question is not in the context, clearly state that.
Always cite specific entities and relationships from the graph in your answer."""
        
        prompt = f"""Context from Knowledge Graph:
{context}

Question: {query}

Please provide a clear, concise answer based on the graph context above."""
        
        return await self.generate(prompt, system_prompt=system_prompt, temperature=0.3)
    
    def _format_graph_context(
        self, 
        nodes: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Format graph data into readable context for LLM"""
        
        context_parts = []
        
        # Format nodes
        if nodes:
            context_parts.append("=== Entities ===")
            for node in nodes:
                labels = node.get("labels", [])
                label = labels[0] if labels else "Entity"
                properties = node.get("properties", {})
                
                # Build node description
                node_desc = f"• {label}"
                
                # Add key properties
                if "name" in properties:
                    node_desc += f": {properties['name']}"
                elif "title" in properties:
                    node_desc += f": {properties['title']}"
                
                # Add other relevant properties
                prop_parts = []
                for key, value in properties.items():
                    if key not in ["id", "name", "title", "embedding"] and value:
                        # Limit property value length
                        str_value = str(value)
                        if len(str_value) > 100:
                            str_value = str_value[:97] + "..."
                        prop_parts.append(f"{key}: {str_value}")
                
                if prop_parts:
                    node_desc += f" ({', '.join(prop_parts)})"
                
                # Add similarity score if available
                if "score" in node and node["score"]:
                    node_desc += f" [relevance: {node['score']:.2f}]"
                
                context_parts.append(node_desc)
        
        # Format relationships
        if relationships:
            context_parts.append("\n=== Relationships ===")
            seen_rels = set()
            for rel in relationships:
                source = rel.get("source", "?")
                target = rel.get("target", "?")
                rel_type = rel.get("type", "RELATED_TO")
                
                # Avoid duplicates
                rel_key = (source, target, rel_type)
                if rel_key in seen_rels:
                    continue
                seen_rels.add(rel_key)
                
                rel_desc = f"• {source} -{rel_type}-> {target}"
                
                # Add relationship properties if any
                rel_props = rel.get("properties", {})
                if rel_props:
                    prop_strs = [f"{k}: {v}" for k, v in rel_props.items() if v]
                    if prop_strs:
                        rel_desc += f" ({', '.join(prop_strs)})"
                
                context_parts.append(rel_desc)
        
        if not context_parts:
            return "No relevant context found in the knowledge graph."
        
        return "\n".join(context_parts)
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Use LLM to extract entities and relationships from text"""
        
        system_prompt = """You are an expert at extracting structured information from text.
Extract entities (people, places, organizations, concepts, etc.) and relationships between them.
Return ONLY valid JSON with this exact structure:
{
  "entities": [
    {"name": "entity name", "type": "Person|Place|Organization|Concept", "description": "brief description"}
  ],
  "relationships": [
    {"source": "entity1 name", "target": "entity2 name", "type": "RELATIONSHIP_TYPE"}
  ]
}"""
        
        prompt = f"""Extract entities and relationships from this text:

{text}

Return only the JSON output, no other text."""
        
        try:
            response = await self.generate(prompt, system_prompt=system_prompt, temperature=0.1)
            
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON in response (handle cases where LLM adds extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.warning("Could not find JSON in LLM response")
                return {"entities": [], "relationships": []}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity extraction JSON: {e}")
            return {"entities": [], "relationships": []}
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {"entities": [], "relationships": []}
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            # Try to list models to verify connection
            await self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
