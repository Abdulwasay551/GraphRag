"""Seed database with sample movie data"""
import asyncio
import sys
import os
import json
import ollama
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.neo4j_service import Neo4jService
from app.services.ollama_service import OllamaService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample movie dataset
SAMPLE_MOVIES = [
    {
        "id": "movie_matrix",
        "title": "The Matrix",
        "year": 1999,
        "tagline": "Welcome to the Real World",
        "plot": "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.",
        "rating": 8.7
    },
    {
        "id": "movie_inception",
        "title": "Inception",
        "year": 2010,
        "tagline": "Your mind is the scene of the crime",
        "plot": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "rating": 8.8
    },
    {
        "id": "movie_interstellar",
        "title": "Interstellar",
        "year": 2014,
        "tagline": "Mankind was born on Earth. It was never meant to die here.",
        "plot": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        "rating": 8.6
    },
    {
        "id": "movie_dark_knight",
        "title": "The Dark Knight",
        "year": 2008,
        "tagline": "Why So Serious?",
        "plot": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
        "rating": 9.0
    },
    {
        "id": "movie_pulp_fiction",
        "title": "Pulp Fiction",
        "year": 1994,
        "tagline": "You won't know the facts until you've seen the fiction",
        "plot": "The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.",
        "rating": 8.9
    }
]

SAMPLE_PEOPLE = [
    {"id": "person_keanu", "name": "Keanu Reeves", "born": 1964, "bio": "Canadian actor known for his roles in action films"},
    {"id": "person_leo", "name": "Leonardo DiCaprio", "born": 1974, "bio": "American actor and environmental activist"},
    {"id": "person_matthew", "name": "Matthew McConaughey", "born": 1969, "bio": "American actor and producer"},
    {"id": "person_christian", "name": "Christian Bale", "born": 1974, "bio": "English actor known for intense method acting"},
    {"id": "person_travolta", "name": "John Travolta", "born": 1954, "bio": "American actor and singer"},
    {"id": "person_wachowski", "name": "Lana Wachowski", "born": 1965, "bio": "American film director and screenwriter"},
    {"id": "person_nolan", "name": "Christopher Nolan", "born": 1970, "bio": "British-American filmmaker known for cerebral narratives"},
    {"id": "person_tarantino", "name": "Quentin Tarantino", "born": 1963, "bio": "American filmmaker known for nonlinear storylines"},
]

SAMPLE_GENRES = [
    {"id": "genre_scifi", "name": "Science Fiction", "description": "Speculative fiction based on scientific concepts"},
    {"id": "genre_action", "name": "Action", "description": "Fast-paced films with physical stunts and chases"},
    {"id": "genre_thriller", "name": "Thriller", "description": "Films designed to hold attention with suspense"},
    {"id": "genre_drama", "name": "Drama", "description": "Serious narrative films"},
    {"id": "genre_crime", "name": "Crime", "description": "Films focused on criminal activities"},
]

# Relationships
ACTING_ROLES = [
    ("person_keanu", "movie_matrix", "Neo"),
    ("person_leo", "movie_inception", "Dom Cobb"),
    ("person_matthew", "movie_interstellar", "Cooper"),
    ("person_christian", "movie_dark_knight", "Bruce Wayne / Batman"),
    ("person_travolta", "movie_pulp_fiction", "Vincent Vega"),
]

DIRECTING_ROLES = [
    ("person_wachowski", "movie_matrix"),
    ("person_nolan", "movie_inception"),
    ("person_nolan", "movie_interstellar"),
    ("person_nolan", "movie_dark_knight"),
    ("person_tarantino", "movie_pulp_fiction"),
]

MOVIE_GENRES = [
    ("movie_matrix", "genre_scifi"),
    ("movie_matrix", "genre_action"),
    ("movie_inception", "genre_scifi"),
    ("movie_inception", "genre_thriller"),
    ("movie_interstellar", "genre_scifi"),
    ("movie_interstellar", "genre_drama"),
    ("movie_dark_knight", "genre_action"),
    ("movie_dark_knight", "genre_crime"),
    ("movie_pulp_fiction", "genre_crime"),
    ("movie_pulp_fiction", "genre_drama"),
]


async def seed_database():
    """Seed database with sample movie data"""
    
    logger.info("Seeding Neo4j database with sample movie data...")
    
    # Connect to Neo4j
    neo4j = Neo4jService(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database
    )
    
    # Connect to Ollama for embeddings
    ollama = OllamaService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout
    )
    
    try:
        await neo4j.connect()
        logger.info("Connected to Neo4j")
        
        # Create movies with embeddings
        logger.info("Creating movie nodes...")
        for movie in SAMPLE_MOVIES:
            # Generate embedding from plot
            text_for_embedding = f"{movie['title']} {movie['plot']}"
            embedding = await ollama.embeddings(text_for_embedding)
            
            movie_data = {**movie, "embedding": embedding}
            await neo4j.create_node("Movie", movie_data, merge_on="id")
            logger.info(f"  ✓ Created: {movie['title']}")
        
        # Create people
        logger.info("Creating person nodes...")
        for person in SAMPLE_PEOPLE:
            await neo4j.create_node("Person", person, merge_on="id")
            logger.info(f"  ✓ Created: {person['name']}")
        
        # Create genres
        logger.info("Creating genre nodes...")
        for genre in SAMPLE_GENRES:
            await neo4j.create_node("Genre", genre, merge_on="id")
            logger.info(f"  ✓ Created: {genre['name']}")
        
        # Create ACTED_IN relationships
        logger.info("Creating ACTED_IN relationships...")
        for person_id, movie_id, character in ACTING_ROLES:
            await neo4j.create_relationship(
                person_id, movie_id, "ACTED_IN",
                {"character": character}
            )
            logger.info(f"  ✓ {person_id} ACTED_IN {movie_id}")
        
        # Create DIRECTED relationships
        logger.info("Creating DIRECTED relationships...")
        for person_id, movie_id in DIRECTING_ROLES:
            await neo4j.create_relationship(
                person_id, movie_id, "DIRECTED"
            )
            logger.info(f"  ✓ {person_id} DIRECTED {movie_id}")
        
        # Create HAS_GENRE relationships
        logger.info("Creating HAS_GENRE relationships...")
        for movie_id, genre_id in MOVIE_GENRES:
            await neo4j.create_relationship(
                movie_id, genre_id, "HAS_GENRE"
            )
            logger.info(f"  ✓ {movie_id} HAS_GENRE {genre_id}")
        
        # Show final stats
        stats = await neo4j.get_graph_stats()
        logger.info("\n✅ Database seeding complete!")
        logger.info(f"📊 Final database stats:")
        logger.info(f"  - Total nodes: {stats['total_nodes']}")
        logger.info(f"  - Total relationships: {stats['total_relationships']}")
        logger.info(f"  - Node labels: {stats['node_labels']}")
        logger.info(f"  - Relationship types: {stats['relationship_types']}")
        
        logger.info("\n🎬 Sample queries you can try:")
        logger.info("  - Who directed The Matrix?")
        logger.info("  - What movies did Leonardo DiCaprio act in?")
        logger.info("  - Tell me about Christopher Nolan's films")
        logger.info("  - What are the best science fiction movies?")
        logger.info("  - Who played Batman in The Dark Knight?")
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise
    
    finally:
        await neo4j.close()
        await ollama.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
