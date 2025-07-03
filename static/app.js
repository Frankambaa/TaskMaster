// Chat application JavaScript
class ChatApp {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        this.isWaiting = false;
        this.init();
    }

    init() {
        // Focus on input
        this.messageInput.focus();
        
        // Add event listeners
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Test connection
        this.testConnection();
    }

    async testConnection() {
        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: 'test' })
            });
            
            if (response.ok) {
                this.showConnectionStatus('Connected', true);
                setTimeout(() => this.hideConnectionStatus(), 2000);
            } else {
                this.showConnectionStatus('Connection Error', false);
            }
        } catch (error) {
            this.showConnectionStatus('Connection Failed', false);
        }
    }

    showConnectionStatus(message, isConnected) {
        this.connectionStatus.querySelector('#statusText').textContent = message;
        this.connectionStatus.className = `connection-status ${isConnected ? 'connected' : ''}`;
        this.connectionStatus.style.display = 'block';
    }

    hideConnectionStatus() {
        this.connectionStatus.style.display = 'none';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isWaiting) return;

        // Add user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.setWaiting(true);

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();

            // Add bot response with typing effect
            if (data.error) {
                this.addMessage(data.error, 'bot', true);
            } else {
                this.addMessage(data.answer, 'bot');
            }

        } catch (error) {
            console.error('Error:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
        } finally {
            this.setWaiting(false);
        }
    }

    addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        if (isError) {
            bubbleDiv.classList.add('error-message');
        } else if (sender === 'bot' && this.isFallbackMessage(text)) {
            bubbleDiv.classList.add('fallback-message');
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();

        contentDiv.appendChild(bubbleDiv);
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        this.chatMessages.appendChild(messageDiv);

        // Typing effect for bot messages
        if (sender === 'bot' && !isError) {
            this.typeMessage(bubbleDiv, text);
        } else {
            bubbleDiv.textContent = text;
        }

        this.scrollToBottom();
    }

    isFallbackMessage(text) {
        const fallbackPhrases = [
            'I couldn\'t find any relevant information',
            'I don\'t have enough information',
            'Please try a different question',
            'I\'m not sure about that'
        ];
        return fallbackPhrases.some(phrase => text.includes(phrase));
    }

    typeMessage(element, text, index = 0) {
        if (index < text.length) {
            element.textContent += text[index];
            setTimeout(() => this.typeMessage(element, text, index + 1), 30);
        }
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    setWaiting(waiting) {
        this.isWaiting = waiting;
        this.sendButton.disabled = waiting;
        this.messageInput.disabled = waiting;
        
        if (waiting) {
            this.sendButton.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
        } else {
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            this.messageInput.focus();
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
}

// Global functions for compatibility
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function sendMessage() {
    if (window.chatApp) {
        window.chatApp.sendMessage();
    }
}

// Initialize the chat app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatApp = new ChatApp();
});
