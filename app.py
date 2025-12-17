from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from pymongo import MongoClient
from openai import OpenAI
import uuid
from datetime import datetime
from config import (
    MONGODB_URI, DATABASE_NAME, COLLECTIONS, 
    OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, OPENAI_CHAT_MODEL,
    VECTOR_SEARCH_INDEX_NAME, MATH_INDEX_NAME, TOP_K_RESULTS
)

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-in-production'  # Change in production
CORS(app)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize MongoDB client
try:
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    print(f"Connected to MongoDB database: {DATABASE_NAME}")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    db = None


def generate_embedding(text):
    """Generate embedding using OpenAI text-embedding-3-small model"""
    try:
        response = openai_client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def vector_search(collection_name, query_embedding, limit=TOP_K_RESULTS):
    """Perform vector search in MongoDB collection using Atlas Vector Search"""
    try:
        collection = db[collection_name]
        
        # Use different index name for Math collection
        if collection_name == 'Math':
            index_name = MATH_INDEX_NAME
        else:
            index_name = VECTOR_SEARCH_INDEX_NAME
        
        # MongoDB Atlas Vector Search pipeline
        # Note: Ensure your MongoDB Atlas collection has a vector search index configured
        # The index should be on the "embedding" field (or adjust "path" below)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": index_name,  # Use Math-specific index for Math collection
                    "path": "embedding",  # Change this if your embedding field has a different name
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,  # Search more candidates for better results
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "text": 1,  # Change "text" if your content field has a different name
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Error in vector search: {e}")
        print(f"Collection: {collection_name}, Index: {index_name if 'index_name' in locals() else 'unknown'}")
        print("Note: Ensure MongoDB Atlas Vector Search index is configured correctly")
        # Return empty list if vector search fails
        return []


def get_relevant_context(subject, user_query):
    """Get relevant context from embedded documents using vector search"""
    collection_name = COLLECTIONS.get(subject)
    if not collection_name:
        return []
    
    # Generate embedding for user query
    query_embedding = generate_embedding(user_query)
    if not query_embedding:
        return []
    
    # Perform vector search
    results = vector_search(collection_name, query_embedding)
    
    # Extract text content from results
    context_texts = [result.get('text', '') for result in results if result.get('text')]
    return context_texts


def create_teaching_prompt(context_texts, conversation_history):
    """Create a comprehensive teaching prompt for GPT-4o mini"""
    
    # Combine context from vector search
    context = "\n\n".join(context_texts) if context_texts else "No specific context available."
    
    system_prompt = f"""You are Habib, an AI tutor for a Higher Secondary School. You are a warm, patient, and encouraging mentor who centers every conversation around the student's learning journey.

Your student-centered teaching philosophy:
1. **Start where the student is**: Acknowledge their question or thought first before diving into explanations. Use phrases like "That's a great question!" or "I love that you're thinking about this!"
2. **Use "you" language**: Speak directly to the student (e.g., "You've just learned that..." instead of "This concept shows that...")
3. **Make it personal and relatable**: Connect concepts to their experiences, interests, or things they already know
4. **Encourage active thinking**: Instead of just explaining, ask "What do you think happens if...?" or "Can you imagine...?"
5. **Validate their efforts**: Celebrate their attempts, questions, and progress, not just correct answers
6. **Check in frequently**: Ask "Does this make sense?" or "What's your take on this?" to ensure they're following along
7. **Empower their curiosity**: Encourage them to ask follow-up questions and explore further
8. **Break it down naturally**: If they seem confused, say things like "Let's pause here - what part would you like me to clarify?" rather than just diving into more detail
9. **Build confidence**: Use positive reinforcement like "You're getting the hang of this!" or "You're thinking like a scientist!"
10. **Be conversational and warm**: Write like you're chatting with a friend who wants to learn, not lecturing

Current topic context from the textbook:
{context}

IMPORTANT: You MUST ONLY answer questions based on the provided textbook context above. If a student asks about something that is NOT covered in the provided context, acknowledge their curiosity first, then gently redirect: "That's an interesting question! Unfortunately, that topic isn't covered in the material we're working with right now. But I'd love to help you understand what IS in the textbook - is there something specific from the material you'd like to explore?"

Remember: The student is the hero of this learning story. Your role is to guide, support, and celebrate their growth. Keep responses conversational, warm, engaging, and always focused on helping THEM understand and succeed."""

    return system_prompt


@app.route('/')
def index():
    """Home page with subject selection"""
    return render_template('index.html')


@app.route('/chat/<subject>')
def chat(subject):
    """Chat interface for selected subject"""
    if subject not in COLLECTIONS:
        return "Invalid subject", 404
    
    # Initialize conversation ID in session if not exists
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
    
    return render_template('chat.html', subject=subject)


@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Handle chat messages and return AI responses"""
    try:
        data = request.json
        user_message = data.get('message', '')
        subject = data.get('subject', '')
        conversation_id = data.get('conversation_id', session.get('conversation_id', str(uuid.uuid4())))
        
        if not user_message or not subject:
            return jsonify({'error': 'Message and subject are required'}), 400
        
        if subject not in COLLECTIONS:
            return jsonify({'error': 'Invalid subject'}), 400
        
        # Get relevant context from vector search
        context_texts = get_relevant_context(subject, user_message)
        
        # Retrieve conversation history from database
        conversations_collection = db['conversations']
        conversation_doc = conversations_collection.find_one({'conversation_id': conversation_id})
        
        # Build conversation history for GPT
        messages = []
        
        # Add system prompt with context
        system_prompt = create_teaching_prompt(context_texts, conversation_doc.get('messages', []) if conversation_doc else [])
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (last 10 messages to avoid token limits)
        if conversation_doc and conversation_doc.get('messages'):
            recent_messages = conversation_doc['messages'][-10:]
            for msg in recent_messages:
                messages.append({"role": msg['role'], "content": msg['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Get response from GPT-4o mini
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        
        # Store conversation in database
        conversation_data = {
            'conversation_id': conversation_id,
            'subject': subject,
            'messages': [
                {
                    'role': 'user',
                    'content': user_message,
                    'timestamp': datetime.utcnow()
                },
                {
                    'role': 'assistant',
                    'content': ai_response,
                    'timestamp': datetime.utcnow()
                }
            ],
            'updated_at': datetime.utcnow()
        }
        
        if conversation_doc:
            # Update existing conversation
            conversations_collection.update_one(
                {'conversation_id': conversation_id},
                {
                    '$push': {'messages': {'$each': conversation_data['messages']}},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
        else:
            # Create new conversation
            conversation_data['created_at'] = datetime.utcnow()
            conversations_collection.insert_one(conversation_data)
        
        return jsonify({
            'response': ai_response,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        print(f"Error in chat API: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Retrieve conversation history"""
    try:
        conversations_collection = db['conversations']
        conversation = conversations_collection.find_one({'conversation_id': conversation_id})
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Convert ObjectId to string and format response
        conversation['_id'] = str(conversation['_id'])
        return jsonify(conversation)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)

