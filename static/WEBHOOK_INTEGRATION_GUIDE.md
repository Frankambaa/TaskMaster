# Webhook Integration Guide

## Overview

The RAG Chatbot now supports comprehensive webhook integration with third-party chat platforms like Freshchat, Zendesk, Intercom, and other customer support systems. This allows external platforms to send messages to the chatbot and receive AI-powered responses back.

## How It Works

### Message Flow
1. **Incoming Messages**: Third-party platform sends user messages to our webhook endpoint
2. **AI Processing**: Messages are processed through the same RAG/AI system as the widget
3. **Response Generation**: AI generates appropriate responses using knowledge base or API tools
4. **Outgoing Messages**: Responses are sent back to the third-party platform
5. **Live Chat Transfer**: When users request human agents, the system can transfer to live chat

### Architecture
```
Third-Party Platform → Webhook Endpoint → RAG/AI System → Response → Third-Party Platform
                                     ↓
                              Live Chat Transfer (if requested)
```

## API Endpoints

### 1. Incoming Webhook
**POST** `/api/webhook/incoming`

Receives messages from third-party platforms.

**Request Format:**
```json
{
    "user_id": "external_user_123",
    "username": "John Doe",
    "message": "Hello, I need help with my account",
    "platform": "freshchat",
    "conversation_id": "conv_456",
    "timestamp": "2025-01-19T12:00:00Z",
    "metadata": {
        "channel": "web",
        "user_agent": "Mozilla/5.0...",
        "custom_fields": {}
    }
}
```

**Response:**
```json
{
    "success": true,
    "response": {
        "answer": "Hello John! I'd be happy to help you with your account. What specific issue are you experiencing?",
        "response_type": "rag_knowledge_base",
        "user_info": {...}
    },
    "message_id": 123,
    "response_id": 124
}
```

### 2. Webhook Configuration
**GET/POST** `/api/webhook/config`

Manage webhook configurations for different platforms.

**Create Configuration:**
```json
{
    "name": "Freshchat Integration",
    "provider": "freshchat",
    "outgoing_webhook_url": "https://your-platform.com/webhook",
    "auth_token": "your_bearer_token",
    "custom_headers": {
        "X-API-Key": "your_api_key",
        "X-Platform": "freshchat"
    },
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "is_active": true
}
```

### 3. Message History
**GET** `/api/webhook/messages`

View webhook message history with filtering options.

**Query Parameters:**
- `platform`: Filter by platform (freshchat, zendesk, etc.)
- `message_type`: incoming, outgoing, agent_outgoing
- `status`: pending, sent, failed, received
- `page`: Page number
- `per_page`: Messages per page

## Integration Examples

### Freshchat Integration

```javascript
// Incoming webhook handler (your platform → our chatbot)
app.post('/freshchat-to-chatbot', async (req, res) => {
    const { user, message, conversation } = req.body;
    
    const webhookPayload = {
        user_id: user.id,
        username: user.name,
        message: message.text,
        platform: 'freshchat',
        conversation_id: conversation.id,
        timestamp: new Date().toISOString(),
        metadata: {
            channel: conversation.channel,
            user_properties: user.properties
        }
    };
    
    try {
        const response = await fetch('https://your-chatbot.com/api/webhook/incoming', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer your_webhook_secret'
            },
            body: JSON.stringify(webhookPayload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // The chatbot response will be sent via outgoing webhook
            res.json({ success: true });
        } else {
            res.status(400).json(result);
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Outgoing webhook handler (our chatbot → your platform)
app.post('/chatbot-to-freshchat', async (req, res) => {
    const { user_id, conversation_id, message, response_type } = req.body;
    
    // Send message to Freshchat
    await freshchatAPI.sendMessage(conversation_id, {
        message_type: 'normal',
        text: message,
        actor_type: 'system'
    });
    
    res.json({ success: true });
});
```

### Zendesk Integration

```python
# Flask example for Zendesk
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/zendesk-to-chatbot', methods=['POST'])
def zendesk_webhook():
    data = request.json
    ticket = data['ticket']
    
    # Extract latest comment
    latest_comment = ticket['comments'][-1]
    
    webhook_payload = {
        'user_id': ticket['requester_id'],
        'username': ticket['requester']['name'],
        'message': latest_comment['body'],
        'platform': 'zendesk',
        'conversation_id': str(ticket['id']),
        'timestamp': latest_comment['created_at'],
        'metadata': {
            'ticket_id': ticket['id'],
            'priority': ticket['priority'],
            'status': ticket['status']
        }
    }
    
    response = requests.post(
        'https://your-chatbot.com/api/webhook/incoming',
        json=webhook_payload,
        headers={'Authorization': 'Bearer your_token'}
    )
    
    return jsonify({'success': True})

@app.route('/chatbot-to-zendesk', methods=['POST'])
def receive_chatbot_response():
    data = request.json
    
    # Add comment to Zendesk ticket
    zendesk_api.tickets.comments.create(
        ticket_id=data['conversation_id'],
        comment={
            'body': data['message'],
            'public': True,
            'author_id': 'your_agent_id'
        }
    )
    
    return jsonify({'success': True})
```

## Configuration Steps

### 1. Set Up Webhook Configuration
1. Access the admin panel at `/admin`
2. Navigate to "Webhook Integration" section
3. Create a new webhook configuration:
   - **Name**: Descriptive name for the integration
   - **Provider**: Platform name (freshchat, zendesk, etc.)
   - **Outgoing Webhook URL**: Where we send responses
   - **Auth Token**: Bearer token for authentication
   - **Custom Headers**: Additional headers if needed
   - **Timeout**: Request timeout in seconds
   - **Retry Attempts**: Number of retries for failed requests

### 2. Configure Third-Party Platform
1. Set up webhook in your platform to send messages to:
   `https://your-chatbot-domain.com/api/webhook/incoming`
2. Configure authentication (Bearer token)
3. Set up endpoint to receive responses from chatbot

### 3. Test Integration
Use the provided test scripts to verify the integration works correctly.

## Live Chat Transfer

When users request live chat (saying phrases like "talk to agent", "live chat", etc.), the system:

1. **Detects Request**: AI recognizes live chat keywords
2. **Creates Session**: Creates a live chat session in the database
3. **Notifies Platform**: Sends notification through webhook
4. **Agent Connection**: Connects user with available agent
5. **Message Routing**: Routes subsequent messages between user and agent

### Live Chat Webhook Payload
```json
{
    "user_id": "external_user_123",
    "conversation_id": "conv_456",
    "platform": "freshchat",
    "message": "Agent is now connected. How can I help you?",
    "sender": "Agent Sarah",
    "sender_type": "agent",
    "timestamp": "2025-01-19T12:05:00Z",
    "session_id": "live_abc123"
}
```

## Security

### Authentication
- Use Bearer tokens for webhook authentication
- Validate webhook signatures if supported by platform
- Implement IP whitelisting for additional security

### Data Protection
- All messages are encrypted in transit (HTTPS)
- User data is stored securely in the database
- No sensitive information is logged in plain text

## Monitoring and Analytics

### Message Tracking
- All webhook messages are stored in the database
- Track message status (pending, sent, failed)
- Monitor response times and success rates

### Error Handling
- Automatic retries for failed webhook deliveries
- Detailed error logging and reporting
- Fallback mechanisms for service unavailability

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Messages**
   - Check webhook URL configuration
   - Verify authentication tokens
   - Check firewall and network settings

2. **Responses Not Being Sent**
   - Verify outgoing webhook URL
   - Check third-party platform API status
   - Review error logs in admin panel

3. **Message Formatting Issues**
   - Ensure JSON payload follows the expected format
   - Check required fields are present
   - Validate data types

### Debug Mode
Enable debug logging to track webhook processing:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For technical support and custom integrations:
- Check the admin panel logs section
- Review webhook message history
- Contact support with specific error messages and platform details

## Limitations

- Maximum message size: 10KB
- Rate limit: 100 requests per minute per platform
- Supported platforms: Any platform that supports webhooks
- Response timeout: 30 seconds default (configurable)