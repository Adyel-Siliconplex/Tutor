// Chat functionality for Habib AI Tutor System

const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function goHome() {
    window.location.href = '/';
}

function addMessage(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'ai'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function showLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loadingIndicator';
    loadingDiv.className = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
    `;
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
}

function removeLoadingIndicator() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Disable input and button
    messageInput.disabled = true;
    sendButton.disabled = true;
    
    // Add user message to chat
    addMessage(message, true);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Show loading indicator
    showLoadingIndicator();
    
    try {
        // Get or create conversation ID
        if (!conversationId) {
            conversationId = generateConversationId();
        }
        
        // Send message to backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                subject: subject,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const data = await response.json();
        
        // Update conversation ID if returned
        if (data.conversation_id) {
            conversationId = data.conversation_id;
        }
        
        // Remove loading indicator
        removeLoadingIndicator();
        
        // Add AI response to chat
        if (data.response) {
            addMessage(data.response, false);
        } else {
            throw new Error('No response received');
        }
        
    } catch (error) {
        console.error('Error:', error);
        removeLoadingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', false);
    } finally {
        // Re-enable input and button
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

function generateConversationId() {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Load conversation history if conversation ID exists
window.addEventListener('DOMContentLoaded', function() {
    messageInput.focus();
    
    // Check if there's a conversation ID in the URL or session
    // This could be enhanced to load previous conversation if needed
});

