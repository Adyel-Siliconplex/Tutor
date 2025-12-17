# Habib Higher Secondary AI Tutor System

An intelligent AI tutoring web application that helps students learn Computer Science and Mathematics using embedded textbook knowledge and OpenAI's GPT-4o mini model.

## Features

- **Subject Selection**: Choose between Computer and Math subjects
- **AI-Powered Teaching**: Uses GPT-4o mini with a gentle, teacher-like approach
- **Vector Search**: Retrieves relevant context from embedded MongoDB documents
- **Conversation History**: Maintains conversation context for personalized learning
- **Comprehension Questions**: AI tutor asks questions to verify student understanding
- **ChatGPT-like Interface**: Modern, intuitive chat interface with maroon theme

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: MongoDB Atlas (with vector search)
- **AI Models**:
  - GPT-4o mini for teaching responses
  - text-embedding-3-small for vector embeddings

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- MongoDB Atlas account with vector search enabled
- OpenAI API key

### Installation

1. **Clone or navigate to the project directory**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   MONGODB_URI=mongodb+srv://devadyel:devadyel@habib.fj7dofe.mongodb.net/?appName=Habib
   ```

4. **Verify MongoDB Configuration**:
   - Ensure your MongoDB collections (`Computer` and `Math`) have vector search indexes configured
   - The embedding field should be named `embedding` (or update `app.py` accordingly)
   - Vector search index name should match `VECTOR_SEARCH_INDEX_NAME` in `config.py`

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   - Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
Tutor/
├── app.py                 # Flask application and API routes
├── config.py             # Configuration and environment variables
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore file
├── static/
│   ├── css/
│   │   └── style.css    # Stylesheet (maroon theme)
│   └── js/
│       └── app.js       # Frontend JavaScript
├── templates/
│   ├── index.html       # Home page (subject selection)
│   └── chat.html        # Chat interface
└── README.md            # This file
```

## MongoDB Vector Search Setup

The application expects:

1. **Database**: `Tutor`
2. **Collections**: `Computer` and `Math` with embedded documents
3. **Vector Search Index**: Configured on the `embedding` field in MongoDB Atlas
4. **Embedding Model**: text-embedding-3-small (1536 dimensions)

### Setting up Vector Search Index in MongoDB Atlas

1. Go to your MongoDB Atlas cluster
2. Navigate to "Atlas Search" in the left sidebar
3. Click "Create Search Index" → "JSON Editor"
4. Create an index with the following configuration (adjust field names if needed):

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    }
  ]
}
```

5. Set the index name (default: `vector_index` or update `VECTOR_SEARCH_INDEX_NAME` in `config.py`)
6. Ensure your documents have an `embedding` field containing the vector array

**Note**: If your collection structure differs (different field names for embeddings or text content), update the `vector_search` function in `app.py` accordingly.

## Usage

1. **Select a Subject**: On the home page, click on either "Computer" or "Math"
2. **Start Learning**: Ask questions about the subject
3. **Get Responses**: The AI tutor responds with explanations based on the embedded textbook content
4. **Answer Questions**: The tutor may ask comprehension questions to check your understanding

## Configuration

Key configuration options in `config.py`:

- `OPENAI_EMBEDDING_MODEL`: Embedding model (text-embedding-3-small)
- `OPENAI_CHAT_MODEL`: Chat model (gpt-4o-mini)
- `VECTOR_SEARCH_INDEX_NAME`: Name of your MongoDB vector search index
- `TOP_K_RESULTS`: Number of relevant document chunks to retrieve (default: 5)

## Notes

- The application uses session storage for conversation management
- Conversations are stored in a `conversations` collection in MongoDB
- The system prompt instructs the AI to be gentle, encouraging, and teacher-like
- Vector search retrieves relevant context before generating responses

## Future Enhancements

- Add more subjects
- User authentication and progress tracking
- Advanced analytics and learning insights
- Mobile app version

## License

This project is for educational purposes.

