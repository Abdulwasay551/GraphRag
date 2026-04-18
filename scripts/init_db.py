"""Initialize Neo4j database with constraints and indices"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.neo4j_service import Neo4jService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with constraints and indices"""
    
    logger.info("Initializing Neo4j database...")
    
    # Connect to Neo4j
    neo4j = Neo4jService(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database
    )
    
    try:
        await neo4j.connect()
        logger.info("Connected to Neo4j")
        
        # Create constraints (ensures uniqueness)
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Genre) REQUIRE g.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                await neo4j.execute_write(constraint)
                logger.info(f"✓ Created constraint: {constraint.split('(')[1].split(')')[0]}")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.info(f"✓ Constraint already exists")
                else:
                    logger.warning(f"✗ Failed to create constraint: {e}")
        
        # Create indices for better query performance
        indices = [
            "CREATE INDEX IF NOT EXISTS FOR (m:Movie) ON (m.title)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (g:Genre) ON (g.name)",
            "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.title)",
        ]
        
        for index in indices:
            try:
                await neo4j.execute_write(index)
                logger.info(f"✓ Created index: {index.split('(')[1].split(')')[0]}")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.info(f"✓ Index already exists")
                else:
                    logger.warning(f"✗ Failed to create index: {e}")
        
        logger.info("✅ Database initialization complete!")
        
        # Show current database stats
        stats = await neo4j.get_graph_stats()
        logger.info(f"Current database stats:")
        logger.info(f"  - Total nodes: {stats['total_nodes']}")
        logger.info(f"  - Total relationships: {stats['total_relationships']}")
        logger.info(f"  - Node labels: {stats['node_labels']}")
        logger.info(f"  - Relationship types: {stats['relationship_types']}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    finally:
        await neo4j.close()


if __name__ == "__main__":
    asyncio.run(init_database())
