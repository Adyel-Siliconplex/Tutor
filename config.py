import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_EMBEDDING_MODEL = 'text-embedding-3-large'  # Changed from text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS = 3072  # Added to match document structure
OPENAI_CHAT_MODEL = 'gpt-4o-mini'

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://devadyel:devadyel@habib.fj7dofe.mongodb.net/?appName=Habib')
DATABASE_NAME = 'Tutor'
COLLECTIONS = {
    'Computer': 'Computer',
    'Math': 'Math'
}

# Vector Search Configuration
# Note: This should match the name of your Vector Search index in MongoDB Atlas
# Math collection uses "topics_1", Computer uses "vector_index"
VECTOR_SEARCH_INDEX_NAME = 'vector_index'  # Default for Computer
MATH_INDEX_NAME = 'topics_1'  # Index name for Math collection
TOP_K_RESULTS = 5  # Number of relevant document chunks to retrieve
MIN_RELEVANCE_SCORE = 0.5  # Minimum similarity score threshold (0-1, higher = more strict)

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

