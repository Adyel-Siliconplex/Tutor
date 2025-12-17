from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from pymongo import MongoClient
from openai import OpenAI
import uuid
from datetime import datetime
import numpy as np
from config import (
    MONGODB_URI, DATABASE_NAME, COLLECTIONS, 
    OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, OPENAI_EMBEDDING_DIMENSIONS, OPENAI_CHAT_MODEL,  # Added OPENAI_EMBEDDING_DIMENSIONS
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
    """Generate embedding using OpenAI text-embedding-3-large model to match document format"""
    try:
        response = openai_client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text,
            dimensions=OPENAI_EMBEDDING_DIMENSIONS  # Specify dimensions to match documents
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot_product / (norm1 * norm2)


def vector_search(collection_name, query_embedding, limit=TOP_K_RESULTS):
    """Perform vector search using manual cosine similarity calculation"""
    try:
        collection = db[collection_name]
        
        # Get all documents with embeddings from the collection
        documents = list(collection.find(
            {"embedding": {"$exists": True}},
            {"text": 1, "embedding": 1, "_id": 0}
        ))
        
        if not documents:
            print(f"No documents with embeddings found in collection: {collection_name}")
            return []
        
        # Calculate cosine similarity for each document
        results = []
        for doc in documents:
            doc_embedding = doc.get('embedding')
            if doc_embedding and doc.get('text'):
                similarity = cosine_similarity(query_embedding, doc_embedding)
                results.append({
                    'text': doc['text'],
                    'score': similarity
                })
        
        # Sort by score (highest first) and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
        
    except Exception as e:
        print(f"Error in vector search: {e}")
        print(f"Collection: {collection_name}")
        import traceback
        traceback.print_exc()
        return []


def get_relevant_context(subject, user_query, min_score=0.3):
    """Get relevant context from embedded documents using vector search"""
    collection_name = COLLECTIONS.get(subject)
    if not collection_name:
        print(f"DEBUG: No collection found for subject: {subject}")
        return []
    
    # Generate embedding for user query with correct dimensions
    query_embedding = generate_embedding(user_query)
    if not query_embedding:
        print(f"DEBUG: Failed to generate embedding for query: {user_query}")
        return []
    
    # Verify embedding dimensions match document structure
    if len(query_embedding) != OPENAI_EMBEDDING_DIMENSIONS:
        print(f"ERROR: Query embedding dimensions ({len(query_embedding)}) don't match expected ({OPENAI_EMBEDDING_DIMENSIONS})")
        return []
    
    # Perform vector search
    results = vector_search(collection_name, query_embedding)
    
    # Debug logging
    if results:
        scores = [result.get('score', 0) for result in results]
        print(f"DEBUG: Query: '{user_query}' | Collection: {collection_name} | Found {len(results)} results")
        print(f"DEBUG: Scores: {[round(s, 4) for s in scores]}")
        print(f"DEBUG: Max score: {round(max(scores), 4) if scores else 0}, Min score: {round(min(scores), 4) if scores else 0}")
    else:
        print(f"DEBUG: No results found for query: '{user_query}' in collection: {collection_name}")
    
    # Filter results by relevance score and extract text content
    # Cosine similarity scores are between -1 and 1, typically 0-1 for normalized embeddings
    # Lower threshold (0.3) to catch more relevant matches
    filtered_results = [
        result for result in results 
        if result.get('score', 0) >= min_score and result.get('text')
    ]
    
    # If filtering removed all results but we had some, use the top result anyway
    # This handles cases where scores are lower than expected but still relevant
    if not filtered_results and results:
        print(f"DEBUG: All results filtered out by score threshold {min_score}, but using top result anyway")
        top_result = results[0]  # Already sorted by score
        if top_result.get('text'):
            filtered_results = [top_result]
    
    context_texts = [result.get('text', '') for result in filtered_results]
    print(f"DEBUG: Returning {len(context_texts)} context chunks after filtering")
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

Current topic context from the Computer Science Grade 12 textbook (National Book Foundation, Federal Textbook Board):
{context}

CRITICAL INSTRUCTION: You MUST ONLY answer questions based on the provided textbook context above. The textbook is "Textbook of Computer Science Grade 12" published by National Book Foundation, Federal Textbook Board, Islamabad (2018). 

If a student asks about something that is NOT covered in the provided context, acknowledge their curiosity first, then gently redirect: "That's an interesting question! Unfortunately, that topic isn't covered in the Grade 12 Computer Science textbook we're working with right now. But I'd love to help you understand what IS in the textbook - is there something specific from the material you'd like to explore?"

You must NOT use any knowledge outside of what's provided in the context. All answers must be grounded strictly in the Computer Science Grade 12 textbook content provided above.

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
        context_texts = get_relevant_context(subject, user_message, min_score=0.3)
        
        # Check if we have relevant context - if not, return out-of-domain message
        if not context_texts:
            out_of_domain_response = (
                "That's an interesting question! Unfortunately, that topic isn't covered "
                "in the material we're working with right now. I can only help you with "
                f"questions about {subject} that are in the textbook. Is there something "
                "specific from the material you'd like to explore?"
            )
            
            # Still store the conversation for history
            conversations_collection = db['conversations']
            conversation_doc = conversations_collection.find_one({'conversation_id': conversation_id})
            
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
                        'content': out_of_domain_response,
                        'timestamp': datetime.utcnow()
                    }
                ],
                'updated_at': datetime.utcnow()
            }
            
            if conversation_doc:
                conversations_collection.update_one(
                    {'conversation_id': conversation_id},
                    {
                        '$push': {'messages': {'$each': conversation_data['messages']}},
                        '$set': {'updated_at': datetime.utcnow()}
                    }
                )
            else:
                conversation_data['created_at'] = datetime.utcnow()
                conversations_collection.insert_one(conversation_data)
            
            return jsonify({
                'response': out_of_domain_response,
                'conversation_id': conversation_id
            })
        
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

