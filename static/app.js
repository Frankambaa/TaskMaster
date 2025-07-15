// Chat application JavaScript
class ChatApp {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.voiceButton = document.getElementById('voiceButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        this.isWaiting = false;
        this.isRecording = false;
        this.recognition = null;
        this.init();
    }

    init() {
        // Focus on input
        this.messageInput.focus();
        
        // Initialize speech recognition
        this.initSpeechRecognition();
        
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

        this.voiceButton.addEventListener('click', () => {
            this.toggleVoiceInput();
        });

        // Test connection
        this.testConnection();
    }

    initSpeechRecognition() {
        // Check if browser supports speech recognition
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            // Configure recognition
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            
            // Event handlers
            this.recognition.onstart = () => {
                this.isRecording = true;
                this.voiceButton.classList.add('recording');
                this.voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
                this.messageInput.placeholder = 'Listening... Speak now!';
            };

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.messageInput.value = transcript;
                this.messageInput.focus();
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.stopRecording();
                
                let errorMessage = 'Voice input failed. ';
                switch(event.error) {
                    case 'network':
                        errorMessage += 'Please check your internet connection.';
                        break;
                    case 'not-allowed':
                        errorMessage += 'Please allow microphone access.';
                        break;
                    case 'no-speech':
                        errorMessage += 'No speech detected. Please try again.';
                        break;
                    default:
                        errorMessage += 'Please try again.';
                }
                
                this.showVoiceError(errorMessage);
            };

            this.recognition.onend = () => {
                this.stopRecording();
            };
        } else {
            // Hide voice button if not supported
            this.voiceButton.style.display = 'none';
            console.warn('Speech recognition not supported in this browser');
        }
    }

    toggleVoiceInput() {
        if (!this.recognition) return;
        
        if (this.isRecording) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }

    stopRecording() {
        this.isRecording = false;
        this.voiceButton.classList.remove('recording');
        this.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        this.messageInput.placeholder = 'Type your message or click the microphone to speak...';
    }

    showVoiceError(message) {
        // Create temporary error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'voice-error';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #dc3545;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.875rem;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 3000);
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
                this.addMessage(data.error, 'bot', true, data.logo);
            } else {
                this.addMessage(data.answer, 'bot', false, data.logo);
            }

        } catch (error) {
            console.error('Error:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true, null);
        } finally {
            this.setWaiting(false);
        }
    }

    addMessage(text, sender, isError = false, logo = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        if (sender === 'user') {
            avatarDiv.innerHTML = '<i class="fas fa-user"></i>';
        } else {
            // For bot messages, use logo if available, otherwise use robot icon
            if (logo) {
                avatarDiv.innerHTML = `<img src="${logo}" alt="Bot" class="message-logo">`;
            } else {
                avatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
            }
        }

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
        } else if (sender === 'bot') {
            // For error messages, still format but don't type
            bubbleDiv.innerHTML = this.formatBotResponse(text);
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
            // Process text character by character but handle formatting
            const currentText = text.substring(0, index + 1);
            element.innerHTML = this.formatBotResponse(currentText);
            setTimeout(() => this.typeMessage(element, text, index + 1), 30);
        }
    }

    formatBotResponse(text) {
        // Convert markdown-like formatting to HTML
        let formatted = text
            // Convert line breaks
            .replace(/\n/g, '<br>')
            // Convert **bold** to <strong>
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Convert *italic* to <em>
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Convert `code` to <code>
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Convert bullet points
            .replace(/^\• (.*?)$/gm, '• $1')
            .replace(/^- (.*?)$/gm, '• $1')
            // Convert numbered lists
            .replace(/^(\d+)\. (.*?)$/gm, '$1. $2');
        
        return formatted;
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

function toggleVoiceInput() {
    if (window.chatApp) {
        window.chatApp.toggleVoiceInput();
    }
}

async function clearMemory() {
    if (confirm('Are you sure you want to clear the conversation memory? This action cannot be undone.')) {
        try {
            const response = await fetch('/clear_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // Clear the visual chat messages
                const chatMessages = document.getElementById('chatMessages');
                chatMessages.innerHTML = `
                    <div class="message bot-message">
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-content">
                            <div class="message-bubble">
                                Hello! I'm your AI assistant. I can help you find information from uploaded documents or have a casual conversation. What would you like to know?
                            </div>
                            <div class="message-time">
                                <span>${new Date().toLocaleTimeString()}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                // Show success message
                const successMessage = document.createElement('div');
                successMessage.className = 'message bot-message';
                successMessage.innerHTML = `
                    <div class="message-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="message-bubble" style="background-color: #d4edda; color: #155724;">
                            <i class="fas fa-check-circle"></i> Conversation memory cleared successfully!
                        </div>
                        <div class="message-time">
                            <span>${new Date().toLocaleTimeString()}</span>
                        </div>
                    </div>
                `;
                chatMessages.appendChild(successMessage);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                // Remove success message after 3 seconds
                setTimeout(() => {
                    successMessage.remove();
                }, 3000);
            } else {
                alert('Error clearing memory: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error clearing memory: ' + error.message);
        }
    }
}

// Initialize the chat app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatApp = new ChatApp();
});
