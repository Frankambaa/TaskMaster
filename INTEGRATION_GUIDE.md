# RAG Chatbot Integration Guide

## Overview

This guide explains how to integrate the enhanced RAG chatbot into external websites with user-specific persistent conversation storage. The chatbot maintains conversation context across sessions and devices when user parameters are provided.

## Enhanced API Features

### User-Specific Persistent Storage
- **Persistent Conversations**: Users can continue conversations across sessions and devices
- **Anonymous Fallback**: Works without user parameters using temporary sessions
- **Privacy Protection**: Each user's conversation data is completely isolated
- **Cross-Device Continuity**: Same user can switch between devices seamlessly

### API Parameters

#### Required Parameters
- `question` (string): The user's question or message

#### Optional User Parameters (for persistent storage)
- `user_id` (string): Unique user identifier from your system
- `username` (string): Display name for the user
- `email` (string): User's email address
- `device_id` (string): Device identifier for cross-device tracking

**Priority Order**: `user_id` > `email` > `device_id`
- The system uses the first available identifier for persistence

## API Endpoints

### 1. Chat Endpoint: `/ask`
Send questions and receive AI responses with conversation context.

**Method**: `POST`
**Content-Type**: `application/json`

#### Request Examples

##### With User Parameters (Persistent)
```json
{
  "question": "What is machine learning?",
  "user_id": "user123",
  "username": "John Doe",
  "email": "john@example.com",
  "device_id": "laptop_001"
}
```

##### Anonymous (Temporary)
```json
{
  "question": "What is machine learning?"
}
```

#### Response Format
```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "status": "success",
  "logo": "/static/logos/logo.png",
  "response_type": "rag",
  "user_info": {
    "user_id": "user123",
    "username": "John Doe",
    "email": "john@example.com",
    "device_id": "laptop_001",
    "session_type": "persistent"
  }
}
```

### 2. Session Info: `/session_info`
Get information about current conversation session.

**Method**: `POST` or `GET`
**Content-Type**: `application/json`

#### Request (POST with user parameters)
```json
{
  "user_id": "user123",
  "username": "John Doe",
  "email": "john@example.com"
}
```

#### Response
```json
{
  "session_type": "persistent",
  "user_identifier": "user123",
  "username": "John Doe",
  "email": "john@example.com",
  "device_id": "laptop_001",
  "stats": {
    "exists": true,
    "type": "user",
    "persistent": true,
    "total_messages": 8,
    "user_messages": 4,
    "ai_messages": 4
  },
  "user_info": {
    "id": 1,
    "user_identifier": "user123",
    "username": "John Doe",
    "email": "john@example.com",
    "device_id": "laptop_001",
    "last_activity": "2024-07-16T09:30:00.000Z",
    "message_count": 8
  }
}
```

### 3. Clear Session: `/clear_session`
Clear conversation history for a user or session.

**Method**: `POST`
**Content-Type**: `application/json`

#### Request
```json
{
  "user_id": "user123",
  "username": "John Doe",
  "email": "john@example.com"
}
```

#### Response
```json
{
  "success": true,
  "message": "User conversation cleared",
  "session_type": "persistent",
  "user_identifier": "user123"
}
```

## Integration Examples

### JavaScript Integration

#### Basic Chat Integration
```javascript
class ChatbotIntegration {
    constructor(baseUrl, userInfo = null) {
        this.baseUrl = baseUrl;
        this.userInfo = userInfo;
    }

    async sendMessage(question) {
        const payload = {
            question: question,
            ...this.userInfo
        };

        try {
            const response = await fetch(`${this.baseUrl}/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    async getSessionInfo() {
        const options = {
            method: this.userInfo ? 'POST' : 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (this.userInfo) {
            options.body = JSON.stringify(this.userInfo);
        }

        try {
            const response = await fetch(`${this.baseUrl}/session_info`, options);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting session info:', error);
            throw error;
        }
    }

    async clearConversation() {
        try {
            const response = await fetch(`${this.baseUrl}/clear_session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.userInfo || {})
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error clearing conversation:', error);
            throw error;
        }
    }
}

// Usage examples
const chatbot = new ChatbotIntegration('http://localhost:5000', {
    user_id: 'user123',
    username: 'John Doe',
    email: 'john@example.com',
    device_id: 'web_browser_001'
});

// Send a message
chatbot.sendMessage('What is artificial intelligence?')
    .then(response => {
        console.log('AI Response:', response.answer);
        console.log('Session Type:', response.user_info.session_type);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```

#### React Component Example
```jsx
import React, { useState, useEffect } from 'react';

const ChatbotComponent = ({ user }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionInfo, setSessionInfo] = useState(null);
    
    const chatbot = new ChatbotIntegration('http://localhost:5000', {
        user_id: user?.id,
        username: user?.name,
        email: user?.email,
        device_id: 'web_app'
    });

    useEffect(() => {
        // Load session info on component mount
        chatbot.getSessionInfo()
            .then(info => setSessionInfo(info))
            .catch(console.error);
    }, []);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMessage = { text: input, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInput('');

        try {
            const response = await chatbot.sendMessage(input);
            const botMessage = { text: response.answer, sender: 'bot' };
            setMessages(prev => [...prev, botMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
        }
    };

    const clearConversation = async () => {
        try {
            await chatbot.clearConversation();
            setMessages([]);
            console.log('Conversation cleared');
        } catch (error) {
            console.error('Error clearing conversation:', error);
        }
    };

    return (
        <div className="chatbot-container">
            <div className="session-info">
                {sessionInfo && (
                    <p>Session: {sessionInfo.session_type} 
                       ({sessionInfo.stats.total_messages} messages)</p>
                )}
            </div>
            
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        {msg.text}
                    </div>
                ))}
            </div>
            
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type your message..."
                />
                <button onClick={sendMessage}>Send</button>
                <button onClick={clearConversation}>Clear</button>
            </div>
        </div>
    );
};

export default ChatbotComponent;
```

### Python Integration

```python
import requests
import json

class ChatbotClient:
    def __init__(self, base_url, user_info=None):
        self.base_url = base_url
        self.user_info = user_info or {}
    
    def send_message(self, question):
        """Send a message to the chatbot"""
        payload = {
            "question": question,
            **self.user_info
        }
        
        response = requests.post(f"{self.base_url}/ask", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_session_info(self):
        """Get current session information"""
        if self.user_info:
            response = requests.post(f"{self.base_url}/session_info", json=self.user_info)
        else:
            response = requests.get(f"{self.base_url}/session_info")
        
        response.raise_for_status()
        return response.json()
    
    def clear_conversation(self):
        """Clear conversation history"""
        response = requests.post(f"{self.base_url}/clear_session", json=self.user_info)
        response.raise_for_status()
        return response.json()

# Usage example
chatbot = ChatbotClient('http://localhost:5000', {
    'user_id': 'user123',
    'username': 'John Doe',
    'email': 'john@example.com',
    'device_id': 'python_client'
})

# Send a message
response = chatbot.send_message("What is machine learning?")
print(f"Response: {response['answer']}")
print(f"Session Type: {response['user_info']['session_type']}")

# Get session info
session_info = chatbot.get_session_info()
print(f"Total messages: {session_info['stats']['total_messages']}")
```

## Implementation Best Practices

### 1. User Identification
- Use consistent user identifiers across your application
- Prefer `user_id` over email for better privacy
- Include device identification for cross-device analytics

### 2. Error Handling
- Always handle API errors gracefully
- Provide fallback behavior for network issues
- Log errors for debugging without exposing sensitive data

### 3. Privacy Considerations
- Only pass necessary user information
- Consider data retention policies
- Implement user consent mechanisms

### 4. Performance Optimization
- Cache user information locally when possible
- Implement request debouncing for rapid typing
- Use appropriate timeout settings

### 5. Session Management
- Regularly check session status
- Provide clear conversation management options
- Handle session expiration gracefully

## Security Considerations

1. **Data Transmission**: Use HTTPS in production
2. **Authentication**: Implement proper authentication in your application
3. **Input Validation**: Validate all user inputs before sending
4. **Rate Limiting**: Implement appropriate rate limiting
5. **Data Privacy**: Follow GDPR and other privacy regulations

## Support and Troubleshooting

### Common Issues

1. **403 Forbidden**: Check CORS settings if calling from browser
2. **500 Internal Server Error**: Verify OpenAI API key is configured
3. **Session not persisting**: Ensure user parameters are consistent
4. **Memory not clearing**: Check user identifier consistency

### Testing

Use the provided `test_user_api.py` script to test integration:

```bash
python test_user_api.py
```

This will verify:
- User-specific persistent conversations
- Anonymous session fallback
- Cross-device conversation continuity
- Privacy-focused session isolation