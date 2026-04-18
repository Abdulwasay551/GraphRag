"""Quick seed database with sample movie data (no embeddings)"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.neo4j_service import Neo4jService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def quick_seed():
    """Seed database with sample data quickly"""
    
    neo4j = Neo4jService(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database
    )
    
    try:
        await neo4j.connect()
        logger.info("Connected to Neo4j")
        
        # Create movies
        movies = [
            ("The Matrix", 1999, "Sci-Fi", "A hacker discovers reality is a simulation", 8.7),
            ("Inception", 2010, "Sci-Fi", "Dream thieves plant ideas in minds", 8.8),
            ("Interstellar", 2014, "Sci-Fi", "Astronauts travel through a wormhole", 8.6),
            ("The Dark Knight", 2008, "Action", "Batman faces the Joker in Gotham", 9.0),
            ("Pulp Fiction", 1994, "Crime", "Interconnected stories of LA criminals", 8.9),
        ]
        
        for title, year, genre, plot, rating in movies:
            query = """
            MERGE (m:Movie {title: $title})
            SET m.year = $year, m.plot = $plot, m.rating = $rating
            MERGE (g:Genre {name: $genre})
            MERGE (m)-[:HAS_GENRE]->(g)
            """
            await neo4j.execute_write(query, {
                "title": title, "year": year, "genre": genre, 
                "plot": plot, "rating": rating
            })
            logger.info(f"✓ Created: {title}")
        
        # Create people and relationships
        people_data = [
            ("Keanu Reeves", "The Matrix", "ACTED_IN"),
            ("Laurence Fishburne", "The Matrix", "ACTED_IN"),
            ("Lana Wachowski", "The Matrix", "DIRECTED"),
            ("Leonardo DiCaprio", "Inception", "ACTED_IN"),
            ("Christopher Nolan", "Inception", "DIRECTED"),
            ("Christopher Nolan", "Interstellar", "DIRECTED"),
            ("Matthew McConaughey", "Interstellar", "ACTED_IN"),
            ("Christian Bale", "The Dark Knight", "ACTED_IN"),
            ("Christopher Nolan", "The Dark Knight", "DIRECTED"),
            ("John Travolta", "Pulp Fiction", "ACTED_IN"),
            ("Samuel L. Jackson", "Pulp Fiction", "ACTED_IN"),
            ("Quentin Tarantino", "Pulp Fiction", "DIRECTED"),
        ]
        
        for person, movie, rel_type in people_data:
            query = f"""
            MERGE (p:Person {{name: $person}})
            MERGE (m:Movie {{title: $movie}})
            MERGE (p)-[:{rel_type}]->(m)
            """
            await neo4j.execute_write(query, {"person": person, "movie": movie})
        
        logger.info(f"✓ Created {len(people_data)} person relationships")
        
        # Create some interesting connections
        connections = [
            ("Christopher Nolan", "Sci-Fi", "KNOWN_FOR"),
            ("Quentin Tarantino", "Crime", "KNOWN_FOR"),
        ]
        
        for person, genre, rel_type in connections:
            query = f"""
            MATCH (p:Person {{name: $person}})
            MATCH (g:Genre {{name: $genre}})
            MERGE (p)-[:{rel_type}]->(g)
            """
            await neo4j.execute_write(query, {"person": person, "genre": genre})
        
        logger.info("✅ Database seeded successfully!")
        logger.info("\nYou can now query:")
        logger.info("  - Who directed The Matrix?")
        logger.info("  - What movies did Christopher Nolan direct?")
        logger.info("  - Tell me about Inception")
        logger.info("  - What Sci-Fi movies are in the database?")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        await neo4j.close()

if __name__ == "__main__":
    asyncio.run(quick_seed())
