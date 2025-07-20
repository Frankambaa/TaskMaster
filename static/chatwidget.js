/**
 * RAG Chatbot Widget - Embeddable Chat Interface
 * 
 * Usage:
 * <script src="chatwidget.js"></script>
 * <script>
 *   ChatWidget.init({
 *     apiUrl: 'http://localhost:5000',
 *     user_id: 'user123',
 *     username: 'John Doe',
 *     email: 'john@example.com',
 *     device_id: 'web_browser_001',
 *     theme: 'light',
 *     position: 'bottom-right'
 *   });
 * </script>
 */

(function() {
    'use strict';

    // Security configuration
    const SECURITY_CONFIG = {
        maxMessageLength: 2000,
        maxConversationHistory: 50,
        rateLimitWindow: 60000, // 1 minute
        rateLimitMaxRequests: 10,
        allowedOrigins: [], // Will be populated with apiUrl domain
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        maxRetries: 3,
        requestTimeout: 30000 // 30 seconds
    };

    // Rate limiting state
    let requestHistory = [];
    let lastActivityTime = Date.now();
    let requestCount = 0;
    let isBlocked = false;

    // Widget configuration
    let config = {
        apiUrl: 'http://localhost:5000',
        user_id: null,
        username: null,
        email: null,
        device_id: null,
        theme: 'light',
        position: 'bottom-right',
        title: 'Chat Assistant',
        welcomeMessage: 'Hi! How can I help you today?',
        apiKey: null, // Optional API key for authentication
        allowedDomains: [], // Domains allowed to use this widget
        persistentHistoryCount: 10, // Number of messages to persist across sessions
        autoScrollToBottom: true, // Automatically scroll to bottom to show latest messages
        smoothScrolling: false, // Use smooth scrolling animation
        showHistoryButton: true, // Show "Load History" button instead of auto-loading
        personalizedWelcome: true, // Show personalized welcome message with user's name
        iconUrl: null, // Custom icon URL for the chat widget toggle button
        widgetSize: 'medium', // Widget size: 'small', 'medium', 'large'
        buttonSize: null, // Toggle button size in pixels (auto-calculated based on widgetSize)
        timeBasedGreeting: true, // Show time-based greeting for first-time users
        voiceEnabled: true, // Enable voice synthesis functionality
        autoPlayVoice: false, // Auto-play bot voice responses
        continuousVoice: false, // Continuous voice conversation mode
        selectedVoice: 'indian_female', // Default voice selection (Indian English female for natural accent)
        showVoiceControls: true // Show voice control buttons in the interface
    };

    // Widget state
    let isOpen = false;
    let isInitialized = false;
    let conversationHistory = [];
    let sessionId = null;
    let ragResponseCount = 0; // Track number of RAG responses for feedback timing
    let isTyping = false; // Track if bot is currently typing
    let chatSettings = {
        typing_effect_enabled: true,
        typing_effect_speed: 25,
        auto_scroll_during_typing: false
    }; // Store backend chat settings
    
    // Voice-related state
    let availableVoices = [];
    let currentAudio = null;
    let isPlayingVoice = false;
    let voicePendingResponses = new Map(); // Track responses pending voice synthesis

    // DOM elements
    let widgetContainer = null;
    let chatWindow = null;
    let messagesContainer = null;
    let inputField = null;
    let sendButton = null;
    let toggleButton = null;
    let customIconImg = null;

    // Security functions
    const SecurityManager = {
        validateConfig: function(options) {
            // Validate API URL
            if (!options.apiUrl || typeof options.apiUrl !== 'string') {
                throw new Error('ChatWidget: apiUrl is required and must be a string');
            }
            
            try {
                const url = new URL(options.apiUrl);
                if (!['http:', 'https:'].includes(url.protocol)) {
                    throw new Error('ChatWidget: apiUrl must use http or https protocol');
                }
            } catch (e) {
                throw new Error('ChatWidget: Invalid apiUrl format');
            }

            // Validate domain restrictions
            if (options.allowedDomains && options.allowedDomains.length > 0) {
                const currentDomain = window.location.hostname;
                if (!options.allowedDomains.includes(currentDomain)) {
                    throw new Error(`ChatWidget: Domain ${currentDomain} is not authorized`);
                }
            }

            // Sanitize user inputs
            if (options.user_id) options.user_id = this.sanitizeInput(options.user_id);
            if (options.username) options.username = this.sanitizeInput(options.username);
            if (options.email) options.email = this.sanitizeInput(options.email);
            if (options.device_id) options.device_id = this.sanitizeInput(options.device_id);
            if (options.title) options.title = this.sanitizeInput(options.title);

            return options;
        },

        sanitizeInput: function(input, isUserInput = true) {
            if (typeof input !== 'string') return input;
            // Apply length limit only for user inputs, not bot responses
            if (isUserInput) {
                return input.replace(/[<>"\'/\\&]/g, '').trim().substring(0, 100);
            } else {
                // For bot responses, only sanitize dangerous characters but don't truncate
                return input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').trim();
            }
        },

        checkRateLimit: function() {
            const now = Date.now();
            
            // Clean old requests
            requestHistory = requestHistory.filter(time => now - time < SECURITY_CONFIG.rateLimitWindow);
            
            // Check rate limit
            if (requestHistory.length >= SECURITY_CONFIG.rateLimitMaxRequests) {
                isBlocked = true;
                setTimeout(() => { isBlocked = false; }, SECURITY_CONFIG.rateLimitWindow);
                return false;
            }
            
            requestHistory.push(now);
            return true;
        },

        validateMessage: function(message) {
            if (!message || typeof message !== 'string') {
                throw new Error('Invalid message format');
            }
            
            if (message.length > SECURITY_CONFIG.maxMessageLength) {
                throw new Error(`Message too long (max ${SECURITY_CONFIG.maxMessageLength} characters)`);
            }
            
            // Basic XSS protection
            const sanitized = message.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
            return sanitized.trim();
        },

        checkSession: function() {
            const now = Date.now();
            if (now - lastActivityTime > SECURITY_CONFIG.sessionTimeout) {
                conversationHistory = [];
                sessionId = null;
                return false;
            }
            lastActivityTime = now;
            return true;
        },

        generateSessionId: function() {
            return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
    };

    // ChatWidget object
    const ChatWidget = {
        init: function(options = {}) {
            if (isInitialized) {
                console.warn('ChatWidget already initialized');
                return;
            }

            try {
                // Validate configuration
                options = SecurityManager.validateConfig(options);
                
                // Merge options with default config
                config = { ...config, ...options };

                // Generate secure session ID
                sessionId = SecurityManager.generateSessionId();

                // Generate device_id if not provided
                if (!config.device_id) {
                    config.device_id = 'web_' + Math.random().toString(36).substr(2, 9);
                }

                // Initialize when DOM is ready
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', () => {
                        this.initializeWidget();
                    });
                } else {
                    this.initializeWidget();
                }
            } catch (error) {
                console.error('ChatWidget initialization failed:', error.message);
                return;
            }
        },

        initializeWidget: function() {
            // Load chat settings and custom icon
            Promise.all([this.loadChatSettings(), this.loadCustomIcon()]).then(() => {
                // Initialize the widget
                this.createStyles();
                this.createWidget();
                this.bindEvents();
                
                isInitialized = true;
                console.log('ChatWidget initialized with settings:', chatSettings);
            }).catch(error => {
                console.error('ChatWidget: Error during initialization:', error);
                // Initialize with defaults
                this.createStyles();
                this.createWidget();
                this.bindEvents();
                
                isInitialized = true;
                console.log('ChatWidget initialized with default settings');
            });
        },

        loadChatSettings: function() {
            return fetch(`${config.apiUrl}/chat_settings`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.settings) {
                    chatSettings = { ...chatSettings, ...data.settings };
                    console.log('ChatWidget: Chat settings loaded:', chatSettings);
                } else {
                    console.warn('ChatWidget: Failed to load settings, using defaults');
                }
            })
            .catch(error => {
                console.error('ChatWidget: Error loading chat settings:', error);
                // Keep default settings
            });
        },

        getWidgetDimensions: function() {
            const sizes = {
                small: { width: 300, height: 400, buttonSize: 60 },
                medium: { width: 350, height: 500, buttonSize: 80 },
                large: { width: 400, height: 600, buttonSize: 100 }
            };
            return sizes[config.widgetSize] || sizes.medium;
        },

        getButtonSize: function() {
            if (config.buttonSize) {
                return config.buttonSize;
            }
            return this.getWidgetDimensions().buttonSize;
        },

        loadCustomIcon: async function() {
            try {
                const response = await fetch(`${config.apiUrl}/api/widget/icon?t=${Date.now()}`); // Cache busting
                const data = await response.json();
                if (data.iconUrl) {
                    config.iconUrl = data.iconUrl;
                    console.log('Custom icon loaded:', data.iconUrl);
                }
            } catch (error) {
                console.log('Could not load custom icon, using default');
            }
        },

        createStyles: function() {
            const style = document.createElement('style');
            style.textContent = `
                .chat-widget-container {
                    position: fixed;
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .chat-widget-container.bottom-right {
                    bottom: 20px;
                    right: 20px;
                }

                .chat-widget-container.bottom-left {
                    bottom: 20px;
                    left: 20px;
                }

                .chat-widget-toggle {
                    width: ${this.getButtonSize()}px;
                    height: ${this.getButtonSize()}px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: ${Math.floor(this.getButtonSize() * 0.4)}px;
                    overflow: hidden;
                }

                .chat-widget-toggle:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
                }

                .chat-widget-window {
                    width: ${this.getWidgetDimensions().width}px;
                    height: ${this.getWidgetDimensions().height}px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    display: none;
                    flex-direction: column;
                    position: absolute;
                    bottom: ${this.getButtonSize() + 20}px;
                    right: 0;
                    overflow: hidden;
                }

                .chat-widget-container.bottom-left .chat-widget-window {
                    right: auto;
                    left: 0;
                }

                .chat-widget-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 16px;
                    font-weight: 600;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chat-widget-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .chat-widget-header-controls {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .chat-widget-voice-btn {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 16px;
                    cursor: pointer;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                    opacity: 0.8;
                }

                .chat-widget-voice-btn:hover {
                    background: rgba(255, 255, 255, 0.1);
                    opacity: 1;
                }

                .chat-widget-voice-btn.active {
                    background: rgba(76, 175, 80, 0.3);
                    opacity: 1;
                }

                .chat-widget-voice-btn.playing {
                    background: rgba(255, 193, 7, 0.3);
                    animation: voice-pulse 1.5s infinite;
                }

                .chat-widget-voice-btn.continuous {
                    background: rgba(76, 175, 80, 0.3);
                    animation: call-pulse 2s infinite;
                }

                .chat-widget-elevenlabs-btn {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 16px;
                    cursor: pointer;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                    opacity: 0.8;
                }

                .chat-widget-elevenlabs-btn:hover {
                    background: rgba(255, 255, 255, 0.1);
                    opacity: 1;
                }

                .chat-widget-elevenlabs-btn.active {
                    background: rgba(156, 39, 176, 0.3);
                    opacity: 1;
                    animation: elevenlabs-pulse 2s infinite;
                }

                @keyframes elevenlabs-pulse {
                    0% { box-shadow: 0 0 0 0 rgba(156, 39, 176, 0.4); }
                    70% { box-shadow: 0 0 0 10px rgba(156, 39, 176, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(156, 39, 176, 0); }
                }

                @keyframes call-pulse {
                    0%, 100% { opacity: 0.8; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.05); }
                }

                .chat-widget-voice-btn.listening {
                    background: rgba(244, 67, 54, 0.3);
                    animation: listening-pulse 1s infinite;
                }

                @keyframes listening-pulse {
                    0%, 100% { opacity: 0.8; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.15); }
                }

                @keyframes voice-pulse {
                    0%, 100% { opacity: 0.8; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.1); }
                }

                .chat-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    background: #f8f9fa;
                }

                .chat-widget-message {
                    margin-bottom: 12px;
                    display: flex;
                    align-items: flex-start;
                }

                .chat-widget-message.user {
                    justify-content: flex-end;
                }

                .chat-widget-message-bubble {
                    max-width: 80%;
                    padding: 10px 14px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                    white-space: pre-wrap;
                    overflow-wrap: break-word;
                }

                .chat-widget-message.user .chat-widget-message-bubble {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .chat-widget-message.bot .chat-widget-message-bubble {
                    background: white;
                    color: #333;
                    border: 1px solid #e0e0e0;
                }

                .chat-widget-input-container {
                    padding: 16px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 8px;
                }

                .chat-widget-input {
                    flex: 1;
                    padding: 10px 14px;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
                    font-size: 14px;
                    outline: none;
                    resize: none;
                    font-family: inherit;
                }

                .chat-widget-input:focus {
                    border-color: #667eea;
                }

                .chat-widget-send {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    transition: all 0.2s ease;
                }

                .chat-widget-send:hover {
                    transform: scale(1.1);
                }

                .chat-widget-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                    transform: none;
                }

                .chat-widget-typing {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    padding: 8px 14px;
                    background: white;
                    border-radius: 18px;
                    margin-bottom: 12px;
                    border: 1px solid #e0e0e0;
                }

                .chat-widget-typing-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #667eea;
                    animation: typing 1.4s infinite ease-in-out;
                }

                .chat-widget-typing-dot:nth-child(1) { animation-delay: -0.32s; }
                .chat-widget-typing-dot:nth-child(2) { animation-delay: -0.16s; }

                @keyframes typing {
                    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
                    40% { transform: scale(1); opacity: 1; }
                }

                .chat-widget-session-info {
                    font-size: 12px;
                    color: #666;
                    padding: 8px 16px;
                    background: #f0f0f0;
                    border-bottom: 1px solid #e0e0e0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chat-widget-clear-btn {
                    background: none;
                    border: none;
                    color: #666;
                    font-size: 12px;
                    cursor: pointer;
                    text-decoration: underline;
                }

                .chat-widget-clear-btn:hover {
                    color: #333;
                }

                @media (max-width: 480px) {
                    .chat-widget-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 100px);
                        bottom: 80px;
                        right: 20px;
                    }

                    .chat-widget-container.bottom-left .chat-widget-window {
                        left: 20px;
                        right: auto;
                    }
                }
            `;
            document.head.appendChild(style);
        },

        createWidget: function() {
            // Create container
            widgetContainer = document.createElement('div');
            widgetContainer.className = `chat-widget-container ${config.position}`;

            // Create toggle button
            toggleButton = document.createElement('button');
            toggleButton.className = 'chat-widget-toggle';
            
            // Use custom icon if provided, otherwise use default emoji
            if (config.iconUrl) {
                // Remove all styling from button - show only the image
                toggleButton.style.background = 'transparent';
                toggleButton.style.border = 'none';
                toggleButton.style.padding = '0';
                toggleButton.style.boxShadow = 'none';
                toggleButton.style.cursor = 'pointer';
                
                // Create the custom icon image once and store it
                customIconImg = document.createElement('img');
                customIconImg.src = config.iconUrl + '?t=' + Date.now(); // Cache busting to ensure new images load
                customIconImg.alt = 'Chat';
                customIconImg.style.cssText = `
                    width: ${this.getButtonSize()}px; 
                    height: ${this.getButtonSize()}px; 
                    object-fit: cover;
                    object-position: center;
                    transition: transform 0.3s ease, filter 0.3s ease;
                    cursor: pointer;
                    pointer-events: none;
                `;
                
                // Add hover effect to the image - simple move animation
                customIconImg.addEventListener('mouseenter', function() {
                    if (!isOpen) {
                        this.style.transform = 'translateY(-2px)';
                    }
                });
                
                customIconImg.addEventListener('mouseleave', function() {
                    if (!isOpen) {
                        this.style.transform = 'translateY(0)';
                    }
                });
                
                toggleButton.appendChild(customIconImg);
            } else {
                toggleButton.innerHTML = '💬';
            }
            
            toggleButton.title = 'Open Chat';

            // Create chat window
            chatWindow = document.createElement('div');
            chatWindow.className = 'chat-widget-window';

            // Create header
            const header = document.createElement('div');
            header.className = 'chat-widget-header';
            header.innerHTML = `
                <span>${config.title}</span>
                <div class="chat-widget-header-controls">
                    <button class="chat-widget-voice-btn" title="Toggle Voice">🎙️</button>
                    <button class="chat-widget-elevenlabs-btn" title="ElevenLabs Voice Agent (Ultra-Fast)">⚡</button>
                    <button class="chat-widget-close">×</button>
                </div>
            `;

            // Create session info
            const sessionInfo = document.createElement('div');
            sessionInfo.className = 'chat-widget-session-info';
            sessionInfo.innerHTML = `
                <span class="session-type">Loading...</span>
                <button class="chat-widget-clear-btn">Clear Chat</button>
            `;

            // Create messages container
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'chat-widget-messages';

            // Create input container
            const inputContainer = document.createElement('div');
            inputContainer.className = 'chat-widget-input-container';

            inputField = document.createElement('textarea');
            inputField.className = 'chat-widget-input';
            inputField.placeholder = 'Type your message...';
            inputField.rows = 1;

            sendButton = document.createElement('button');
            sendButton.className = 'chat-widget-send';
            sendButton.innerHTML = '➤';
            sendButton.title = 'Send message';

            // Assemble the widget
            inputContainer.appendChild(inputField);
            inputContainer.appendChild(sendButton);

            chatWindow.appendChild(header);
            chatWindow.appendChild(sessionInfo);
            chatWindow.appendChild(messagesContainer);
            chatWindow.appendChild(inputContainer);

            widgetContainer.appendChild(toggleButton);
            widgetContainer.appendChild(chatWindow);

            // Add to page (ensure body exists)
            if (document.body) {
                document.body.appendChild(widgetContainer);
            } else {
                console.error('ChatWidget: document.body not available');
                return;
            }

            // Always show personalized welcome message first
            if (config.welcomeMessage) {
                const welcomeMsg = this.getPersonalizedWelcome();
                this.addMessage(welcomeMsg, 'bot');
                
                // Check if we should show load history button
                if (config.showHistoryButton) {
                    this.checkForHistoryAndShowButton();
                } else {
                    // Auto-load history if button is disabled
                    this.loadChatHistory().then((historyLoaded) => {
                        if (historyLoaded) {
                            // Remove welcome message if history was loaded
                            const welcomeMessages = messagesContainer.querySelectorAll('.chat-widget-message.bot');
                            if (welcomeMessages.length > 0) {
                                welcomeMessages[0].remove();
                            }
                        }
                    });
                }
            }
            
            // Ensure we scroll to bottom after everything is loaded
            setTimeout(() => {
                this.scrollToBottom();
            }, 100);

            // Load session info
            this.loadSessionInfo();
        },

        bindEvents: function() {
            // Toggle button
            toggleButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleWidget();
            });

            // Close button
            chatWindow.querySelector('.chat-widget-close').addEventListener('click', () => {
                this.closeWidget();
            });

            // Voice button
            const voiceBtn = chatWindow.querySelector('.chat-widget-voice-btn');
            if (voiceBtn) {
                voiceBtn.addEventListener('click', () => {
                    // If in continuous voice mode, disconnect
                    if (config.continuousVoice) {
                        this.disconnectVoiceMode();
                    } else if (isPlayingVoice) {
                        // Stop current audio playback
                        this.stopVoice();
                    } else {
                        // Start continuous voice conversation mode
                        this.startContinuousVoiceMode();
                    }
                });
                
                // Initialize voice controls appearance
                this.updateVoiceControls();
            }

            // ElevenLabs Embedded Agent button
            const elevenlabsBtn = chatWindow.querySelector('.chat-widget-elevenlabs-btn');
            if (elevenlabsBtn) {
                elevenlabsBtn.addEventListener('click', () => {
                    this.toggleElevenLabsEmbedded();
                });
            }

            // Clear button (add error handling since it might not exist)
            const clearBtn = chatWindow.querySelector('.chat-widget-clear-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearConversation();
                });
            }

            // Send button
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });

            // Input field
            inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            inputField.addEventListener('input', () => {
                inputField.style.height = 'auto';
                inputField.style.height = Math.min(inputField.scrollHeight, 100) + 'px';
            });

            // Click outside to close
            document.addEventListener('click', (e) => {
                if (isOpen && !widgetContainer.contains(e.target)) {
                    // Don't close if clicking on feedback buttons or chat close buttons
                    if (e.target.closest('.chat-close-buttons') || e.target.closest('.feedback-buttons')) {
                        return;
                    }
                    this.closeWidget();
                }
            });
        },

        toggleWidget: function() {
            if (isOpen) {
                this.closeWidget();
            } else {
                this.openWidget();
            }
        },

        openWidget: function() {
            chatWindow.style.display = 'flex';
            
            // Update toggle button to show close icon
            if (config.iconUrl && customIconImg) {
                // For custom icons, just darken the image slightly to indicate it's active
                customIconImg.alt = 'Close Chat';
                customIconImg.style.filter = 'brightness(0.7) contrast(1.1)';
                customIconImg.style.transform = 'translateY(0)'; // Reset hover effect
            } else {
                toggleButton.innerHTML = '×';
            }
            toggleButton.title = 'Close Chat';
            isOpen = true;
            
            // Focus input and scroll to bottom
            setTimeout(() => {
                inputField.focus();
                // Ensure we scroll to the bottom when opening
                this.scrollToBottom();
            }, 100);
        },

        closeWidget: function() {
            console.log('closeWidget() called - chat will be closed');
            console.trace('closeWidget called from:');
            chatWindow.style.display = 'none';
            
            // Update toggle button to show chat icon
            if (config.iconUrl && customIconImg) {
                // For custom icons, restore original appearance
                customIconImg.alt = 'Chat';
                customIconImg.style.filter = 'none';
                customIconImg.style.transform = 'translateY(0)'; // Reset position
            } else {
                toggleButton.innerHTML = '💬';
            }
            toggleButton.title = 'Open Chat';
            isOpen = false;
        },

        scrollToBottom: function(forceSmooth = null) {
            if (messagesContainer && config.autoScrollToBottom) {
                const useSmooth = forceSmooth !== null ? forceSmooth : config.smoothScrolling;
                if (useSmooth) {
                    messagesContainer.scrollTo({
                        top: messagesContainer.scrollHeight,
                        behavior: 'smooth'
                    });
                } else {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }
        },

        getTimeBasedGreeting: function() {
            if (!config.timeBasedGreeting) {
                return '';
            }
            
            const now = new Date();
            const hour = now.getHours();
            
            if (hour >= 5 && hour < 12) {
                return 'Good morning! ';
            } else if (hour >= 12 && hour < 17) {
                return 'Good afternoon! ';
            } else if (hour >= 17 && hour < 22) {
                return 'Good evening! ';
            } else {
                return 'Hello! '; // Late night/early hours
            }
        },

        getPersonalizedWelcome: function() {
            let greeting = '';
            let name = '';
            
            // Get time-based greeting for first-time users
            if (config.timeBasedGreeting) {
                // Check if this is a first-time user (no persistent history)
                const isFirstTime = !localStorage.getItem(`chatwidget_visited_${config.user_id || config.email || config.device_id || 'anonymous'}`);
                if (isFirstTime) {
                    greeting = this.getTimeBasedGreeting();
                    // Mark user as visited
                    localStorage.setItem(`chatwidget_visited_${config.user_id || config.email || config.device_id || 'anonymous'}`, 'true');
                }
            }
            
            // Get personalized name
            if (config.personalizedWelcome) {
                if (config.username) {
                    name = config.username;
                } else if (config.email) {
                    name = config.email.split('@')[0];
                } else if (config.user_id) {
                    name = config.user_id;
                }
            }
            
            // Combine greeting with personalization
            if (greeting && name) {
                return `${greeting}${name}! How can I help you today?`;
            } else if (greeting) {
                return `${greeting}How can I help you today?`;
            } else if (name) {
                return `Hi ${name}! How can I help you today?`;
            }
            
            return config.welcomeMessage;
        },

        checkForHistoryAndShowButton: function() {
            // Check if there's history available without loading it
            if (!config.user_id && !config.email && !config.device_id) {
                return;
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                limit: 1 // Just check if any history exists
            };

            fetch(`${config.apiUrl}/widget_history`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.history && Array.isArray(data.history) && data.history.length > 0) {
                    // History exists, show the button
                    this.addLoadHistoryButton();
                }
            })
            .catch(error => {
                console.error('Error checking for history:', error);
            });
        },

        addLoadHistoryButton: function() {
            const buttonDiv = document.createElement('div');
            buttonDiv.className = 'chat-widget-message bot';
            buttonDiv.style.textAlign = 'center';
            buttonDiv.style.marginTop = '5px';
            buttonDiv.style.marginBottom = '10px';
            
            const button = document.createElement('button');
            button.className = 'load-history-btn';
            button.textContent = 'Load Previous Messages';
            button.style.cssText = `
                background: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                padding: 6px 12px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s;
                box-shadow: none;
                outline: none;
            `;
            
            button.addEventListener('mouseover', () => {
                button.style.backgroundColor = '#e9ecef';
                button.style.borderColor = '#adb5bd';
            });
            
            button.addEventListener('mouseout', () => {
                button.style.backgroundColor = '#f8f9fa';
                button.style.borderColor = '#dee2e6';
            });
            
            button.addEventListener('click', () => {
                button.textContent = 'Loading...';
                button.disabled = true;
                button.style.cursor = 'not-allowed';
                this.loadChatHistoryOnDemand().then(() => {
                    buttonDiv.remove();
                });
            });
            
            buttonDiv.appendChild(button);
            
            // Insert button before the welcome message
            const welcomeMessage = messagesContainer.querySelector('.chat-widget-message.bot');
            if (welcomeMessage) {
                messagesContainer.insertBefore(buttonDiv, welcomeMessage);
            } else {
                messagesContainer.appendChild(buttonDiv);
            }
            
            this.scrollToBottom();
        },

        addMessage: function(text, sender, isError = false, enableTyping = false, storeInHistory = true, responseData = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-widget-message ${sender}`;
            
            const bubble = document.createElement('div');
            bubble.className = 'chat-widget-message-bubble';
            
            if (isError) {
                bubble.style.background = '#ffebee';
                bubble.style.color = '#c62828';
                bubble.style.border = '1px solid #ffcdd2';
            }
            
            messageDiv.appendChild(bubble);
            messagesContainer.appendChild(messageDiv);
            
            // Store in history with security limits (only for new messages, not loaded history)
            if (storeInHistory) {
                conversationHistory.push({ 
                    text: SecurityManager.sanitizeInput(text, sender === 'user'), 
                    sender, 
                    timestamp: new Date().toISOString(),
                    sessionId: sessionId
                });
                
                // Limit conversation history size
                if (conversationHistory.length > SECURITY_CONFIG.maxConversationHistory) {
                    conversationHistory = conversationHistory.slice(-SECURITY_CONFIG.maxConversationHistory);
                }
            }
            
            // Enable typing effect for bot messages based on backend settings
            if (chatSettings.typing_effect_enabled && enableTyping && sender === 'bot') {
                isTyping = true; // Set typing state
                this.typeMessage(bubble, text, 0, responseData);
            } else {
                bubble.innerHTML = this.formatMessage(text, sender === 'user');
                
                // Add feedback buttons for RAG responses (only for new bot messages and after 3+ conversations)
                if (sender === 'bot' && storeInHistory && responseData && this.shouldShowFeedback(responseData)) {
                    this.addFeedbackButtons(messageDiv, text, responseData);
                }
                
                // Scroll to bottom
                this.scrollToBottom();
            }
        },

        typeMessage: function(element, text, index = 0, responseData = null) {
            const formattedText = this.formatMessage(text, false); // false = not user input
            
            // Simple character-by-character typing for better compatibility
            const plainText = text.replace(/\*\*(.*?)\*\*/g, '$1')
                                 .replace(/\*(.*?)\*/g, '$1')
                                 .replace(/`(.*?)`/g, '$1');
            
            if (index < plainText.length) {
                const currentText = plainText.substring(0, index + 1);
                
                // Apply formatting to the current text without truncation
                const displayText = SecurityManager.sanitizeInput(currentText, false)
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>')
                    .replace(/(https?:\/\/[^\s<>"{}|\\^`[\]]+)/gi, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">$1</a>');
                
                element.innerHTML = displayText;
                
                // Only auto-scroll during typing if setting is enabled
                if (chatSettings.auto_scroll_during_typing) {
                    this.scrollToBottom();
                }
                
                // Continue typing with backend-configured speed
                setTimeout(() => {
                    this.typeMessage(element, text, index + 1, responseData);
                }, chatSettings.typing_effect_speed || 25);
            } else {
                // Typing complete - apply full formatting and finalize
                isTyping = false; // Clear typing state
                element.innerHTML = formattedText;
                
                // Always scroll to bottom when typing is complete
                this.scrollToBottom();
                
                // Add feedback buttons for RAG responses after typing is complete (only after 3+ conversations)
                if (responseData && this.shouldShowFeedback(responseData)) {
                    const messageDiv = element.closest('.chat-widget-message');
                    this.addFeedbackButtons(messageDiv, text, responseData);
                }
            }
        },

        formatMessage: function(text, isUserInput = false) {
            // Sanitize and format text for display
            const sanitized = SecurityManager.sanitizeInput(text, isUserInput);
            
            // Apply URL linking and other formatting for bot responses
            return sanitized
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>')
                .replace(/(https?:\/\/[^\s<>"{}|\\^`[\]]+)/gi, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">$1</a>');
        },

        showTyping: function() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-widget-typing';
            typingDiv.innerHTML = `
                <div class="chat-widget-typing-dot"></div>
                <div class="chat-widget-typing-dot"></div>
                <div class="chat-widget-typing-dot"></div>
            `;
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            return typingDiv;
        },

        hideTyping: function(typingDiv) {
            if (typingDiv && typingDiv.parentNode) {
                typingDiv.parentNode.removeChild(typingDiv);
            }
        },

        sendMessage: function() {
            const message = inputField.value.trim();
            if (!message) return;

            try {
                // Security validations
                if (isBlocked) {
                    this.addMessage('Rate limit exceeded. Please wait before sending another message.', 'bot', true);
                    return;
                }

                if (!SecurityManager.checkRateLimit()) {
                    this.addMessage('Too many requests. Please wait a moment before trying again.', 'bot', true);
                    return;
                }

                if (!SecurityManager.checkSession()) {
                    this.addMessage('Session expired. Please refresh the page to continue.', 'bot', true);
                    return;
                }

                // Validate and sanitize message
                const sanitizedMessage = SecurityManager.validateMessage(message);
                if (!sanitizedMessage) {
                    this.addMessage('Invalid message format. Please try again.', 'bot', true);
                    return;
                }

                // Disable input
                inputField.disabled = true;
                sendButton.disabled = true;

                // Add user message
                this.addMessage(sanitizedMessage, 'user');
                
                // Clear input
                inputField.value = '';
                inputField.style.height = 'auto';

                // Show typing indicator
                const typingDiv = this.showTyping();

                // Send to API
                this.sendToAPI(sanitizedMessage).then(response => {
                    this.hideTyping(typingDiv);
                    
                    // Track RAG responses for feedback timing and add user question for feedback
                    const responseData = { ...response, user_question: sanitizedMessage };
                    if (this.isRAGResponse(responseData)) {
                        this.trackRAGResponse();
                    }
                    
                    // Pass the full response data including user question for feedback
                    this.addMessage(response.answer, 'bot', false, true, true, responseData); // Enable typing effect with response data
                    this.updateSessionInfo(response.user_info);
                    
                    // Handle voice synthesis if enabled and voice data is available
                    if (config.voiceEnabled && response.voice_data) {
                        this.handleVoiceResponse(response.voice_data, response.answer);
                    } else if (config.voiceEnabled && config.autoPlayVoice) {
                        // Fallback: synthesize voice for the text response
                        this.synthesizeVoice(response.answer);
                    }
                }).catch(error => {
                    this.hideTyping(typingDiv);
                    this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
                    console.error('Chat error:', error);
                }).finally(() => {
                    // Re-enable input
                    inputField.disabled = false;
                    sendButton.disabled = false;
                    inputField.focus();
                });

            } catch (error) {
                this.addMessage(error.message, 'bot', true);
                console.error('Security validation failed:', error);
            }
        },

        sendToAPI: function(question) {
            const payload = {
                question: question,
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                session_id: sessionId,
                timestamp: Date.now(),
                voice_enabled: config.voiceEnabled,
                voice: config.selectedVoice
            };

            // Build headers
            const headers = {
                'Content-Type': 'application/json',
                'X-Widget-Origin': window.location.origin,
                'X-Widget-Referrer': window.location.href,
                'X-Widget-User-Agent': navigator.userAgent
            };

            // Add API key if configured
            if (config.apiKey) {
                headers['Authorization'] = `Bearer ${config.apiKey}`;
            }

            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), SECURITY_CONFIG.requestTimeout);

            return fetch(`${config.apiUrl}/ask`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload),
                signal: controller.signal,
                credentials: 'same-origin'
            }).then(response => {
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                // Validate response content type
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Invalid response format');
                }
                
                return response.json();
            }).then(data => {
                // Basic response validation
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response data');
                }
                
                return data;
            }).catch(error => {
                clearTimeout(timeoutId);
                
                if (error.name === 'AbortError') {
                    throw new Error('Request timeout');
                }
                
                throw error;
            });
        },

        // Voice synthesis methods
        loadAvailableVoices: function() {
            if (availableVoices.length > 0) {
                return Promise.resolve(availableVoices);
            }
            
            return fetch(`${config.apiUrl}/api/voice/available_voices`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.voices) {
                        availableVoices = data.voices;
                        return availableVoices;
                    }
                    throw new Error('Failed to load voices');
                })
                .catch(error => {
                    console.error('Error loading voices:', error);
                    return [];
                });
        },

        synthesizeVoice: function(text) {
            if (!config.voiceEnabled || isPlayingVoice) {
                return Promise.resolve();
            }

            return new Promise((resolve, reject) => {
                isPlayingVoice = true;
                this.updateVoiceControls();

                // Stop speech recognition while speaking to prevent feedback
                if (window.currentSpeechRecognition && config.continuousVoice) {
                    console.log('Pausing speech recognition during voice output');
                    window.currentSpeechRecognition.stop();
                    window.speechRecognitionPaused = true;
                }

                fetch(`${config.apiUrl}/api/voice/synthesize`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Widget-Origin': window.location.origin
                    },
                    body: JSON.stringify({
                        text: text,
                        voice: config.selectedVoice
                    })
                })
                .then(response => {
                    if (response.ok) {
                        return response.blob();
                    }
                    throw new Error('Voice synthesis failed');
                })
                .then(audioBlob => {
                    return this.playAudioBlob(audioBlob);
                })
                .then(() => {
                    isPlayingVoice = false;
                    this.updateVoiceControls();

                    // Resume speech recognition after voice output finishes
                    if (window.speechRecognitionPaused && config.continuousVoice) {
                        console.log('Resuming speech recognition after voice output');
                        window.speechRecognitionPaused = false;
                        setTimeout(() => {
                            this.startSpeechRecognition();
                        }, 1000); // 1 second delay for more natural conversation flow
                    }

                    resolve();
                })
                .catch(error => {
                    console.error('Voice synthesis error:', error);
                    isPlayingVoice = false;
                    this.updateVoiceControls();

                    // Resume speech recognition even if voice fails
                    if (window.speechRecognitionPaused && config.continuousVoice) {
                        window.speechRecognitionPaused = false;
                        setTimeout(() => {
                            this.startSpeechRecognition();
                        }, 1000);
                    }

                    reject(error);
                });
            });
        },

        handleVoiceResponse: function(voiceData, text) {
            if (!config.voiceEnabled) return;
            
            if (voiceData.audio_file && config.autoPlayVoice) {
                // If we have a pre-generated audio file, fetch and play it
                fetch(voiceData.audio_file)
                    .then(response => response.blob())
                    .then(audioBlob => this.playAudioBlob(audioBlob))
                    .catch(error => {
                        console.error('Error playing voice response:', error);
                        // Fallback to text synthesis
                        this.synthesizeVoice(text);
                    });
            }
        },

        playAudioBlob: function(audioBlob) {
            return new Promise((resolve, reject) => {
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                
                const audioUrl = URL.createObjectURL(audioBlob);
                currentAudio = new Audio(audioUrl);
                
                currentAudio.addEventListener('loadstart', () => {
                    console.log('Audio loading started');
                });
                
                currentAudio.addEventListener('ended', () => {
                    console.log('Audio playback ended');
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                    resolve();
                });
                
                currentAudio.addEventListener('error', () => {
                    console.error('Audio playback error');
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                    reject(new Error('Audio playback failed'));
                });
                
                currentAudio.play().then(() => {
                    console.log('Audio playback started successfully');
                }).catch(error => {
                    console.error('Audio play failed:', error);
                    URL.revokeObjectURL(audioUrl);
                    currentAudio = null;
                    reject(error);
                });
            });
        },

        stopVoice: function() {
            console.log('Stopping voice playback');
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0; // Reset to beginning
                currentAudio = null;
                isPlayingVoice = false;
                this.updateVoiceControls();
                console.log('Voice playback stopped successfully');
            }
        },

        toggleVoice: function() {
            config.voiceEnabled = !config.voiceEnabled;
            
            if (!config.voiceEnabled && currentAudio) {
                this.stopVoice();
            }
            
            this.updateVoiceControls();
        },

        // ElevenLabs Embedded Agent Integration
        toggleElevenLabsEmbedded: function() {
            if (config.elevenlabsEmbeddedActive) {
                this.disconnectElevenLabsEmbedded();
            } else {
                this.startElevenLabsEmbedded();
            }
        },

        startElevenLabsEmbedded: function() {
            if (config.elevenlabsEmbeddedActive) {
                console.log('ElevenLabs embedded agent already active');
                return;
            }

            console.log('Starting ElevenLabs embedded voice agent');
            config.elevenlabsEmbeddedActive = true;
            
            this.updateElevenLabsEmbeddedControls();
            this.addBotMessage("⚡ Ultra-fast ElevenLabs Voice Agent activated! I'm Ria from Apna. Speak directly for instant responses.");
            
            // Initialize embedded agent with your agent ID
            this.initializeElevenLabsEmbedded('agent_01jzswcbh0ej5svsc36s12hmsv');
        },

        disconnectElevenLabsEmbedded: function() {
            console.log('Disconnecting ElevenLabs embedded agent');
            
            config.elevenlabsEmbeddedActive = false;
            
            // Close embedded agent widget if exists
            if (window.elevenLabsEmbeddedWidget) {
                try {
                    window.elevenLabsEmbeddedWidget.endSession();
                } catch (e) {
                    console.log('Error ending embedded session:', e);
                }
                window.elevenLabsEmbeddedWidget = null;
            }
            
            // Update UI
            this.updateElevenLabsEmbeddedControls();
            
            // Add disconnection message
            this.addMessage("📴 ElevenLabs Voice Agent disconnected.", 'bot', false, false);
        },

        updateElevenLabsEmbeddedControls: function() {
            const elevenlabsBtn = document.querySelector('.chat-widget-elevenlabs-btn');
            if (elevenlabsBtn) {
                if (config.elevenlabsEmbeddedActive) {
                    elevenlabsBtn.classList.add('active');
                    elevenlabsBtn.title = 'Disconnect ElevenLabs Voice';
                    elevenlabsBtn.innerHTML = '🔊'; // Change icon when active
                } else {
                    elevenlabsBtn.classList.remove('active');
                    elevenlabsBtn.title = 'ElevenLabs Voice Agent (Ultra-Fast)';
                    elevenlabsBtn.innerHTML = '⚡'; // Default icon
                }
            }
        },

        initializeElevenLabsEmbedded: function(agentId) {
            console.log('Initializing ElevenLabs embedded agent with ID:', agentId);
            
            // Get signed URL for the agent
            fetch(`${config.apiUrl}/api/elevenlabs/signed_url`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify({
                    agent_id: agentId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data.signed_url) {
                    this.loadElevenLabsEmbeddedWidget(data.data.signed_url, agentId);
                } else {
                    console.error('Failed to get signed URL:', data.error);
                    this.addMessage('❌ Failed to initialize ElevenLabs agent: ' + (data.error || 'Unknown error'), 'bot');
                }
            })
            .catch(error => {
                console.error('Network error getting signed URL:', error);
                this.addMessage('❌ Network error initializing ElevenLabs agent', 'bot');
            });
        },

        loadElevenLabsEmbeddedWidget: function(signedUrl, agentId) {
            console.log('Loading ElevenLabs embedded widget with signed URL');
            
            // Create or update embedded widget container
            let widgetContainer = document.getElementById('elevenlabs-embedded-container');
            if (!widgetContainer) {
                widgetContainer = document.createElement('div');
                widgetContainer.id = 'elevenlabs-embedded-container';
                widgetContainer.style.cssText = `
                    position: fixed;
                    bottom: 120px;
                    right: 20px;
                    width: 350px;
                    height: 400px;
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    border-radius: 15px;
                    padding: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    color: white;
                    font-family: Arial, sans-serif;
                    z-index: 10001;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                `;
                document.body.appendChild(widgetContainer);
            }
            
            widgetContainer.innerHTML = `
                <h4 style="margin: 0 0 15px 0; text-align: center;">⚡ ElevenLabs Voice Agent</h4>
                <p style="margin: 0 0 15px 0; text-align: center; font-size: 14px;">Ultra-fast voice processing (~75ms latency)</p>
                <div style="margin: 15px 0; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px; text-align: center;">
                    <strong>🔗 Agent ID:</strong><br>
                    <small>${agentId}</small><br><br>
                    <strong>🔗 Status:</strong><br>
                    <small>Connected & Ready</small>
                </div>
                <p style="margin: 15px 0 0 0; text-align: center; font-size: 12px; opacity: 0.8;">
                    Speak directly for instant AI responses<br>
                    No delays - Native ElevenLabs processing
                </p>
            `;
            
            // Store widget reference for cleanup
            window.elevenLabsEmbeddedWidget = {
                container: widgetContainer,
                signedUrl: signedUrl,
                agentId: agentId,
                endSession: function() {
                    if (this.container && this.container.parentNode) {
                        this.container.parentNode.removeChild(this.container);
                    }
                }
            };
            
            // Add close handler to widget
            widgetContainer.addEventListener('click', (e) => {
                if (e.target === widgetContainer) {
                    ChatWidget.disconnectElevenLabsEmbedded();
                }
            });
            
            console.log('ElevenLabs embedded widget loaded successfully');
        },

        playElevenLabsAudio: function(audioBlob) {
            return new Promise((resolve, reject) => {
                // Stop any existing ElevenLabs audio
                if (window.elevenLabsCurrentAudio) {
                    window.elevenLabsCurrentAudio.pause();
                    window.elevenLabsCurrentAudio.currentTime = 0;
                    window.elevenLabsCurrentAudio = null;
                }

                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                
                // Store reference for potential interruption
                window.elevenLabsCurrentAudio = audio;
                
                audio.onended = () => {
                    console.log('ElevenLabs audio playback completed');
                    URL.revokeObjectURL(audioUrl);
                    window.elevenLabsCurrentAudio = null;
                    
                    // Resume speech recognition after audio ends
                    window.speechRecognitionPaused = false;
                    
                    // Auto-restart listening after audio ends with much longer delay to prevent speaker feedback
                    if (config.elevenlabsActive && !window.voiceManuallyDisconnected && !window.currentSpeechRecognition) {
                        setTimeout(() => {
                            if (config.elevenlabsActive && !window.currentSpeechRecognition && !window.elevenLabsCurrentAudio) {
                                console.log('🎤 RESUMING speech recognition after speaker audio finished');
                                this.startElevenLabsSpeechRecognition();
                            }
                        }, 5000); // Much longer delay to ensure speaker audio doesn't interfere
                    }
                    
                    resolve();
                };

                audio.onerror = (error) => {
                    console.error('ElevenLabs audio playback error:', error);
                    URL.revokeObjectURL(audioUrl);
                    window.elevenLabsCurrentAudio = null;
                    window.speechRecognitionPaused = false; // Resume on error
                    reject(error);
                };

                // CRITICAL: Stop speech recognition BEFORE audio starts to prevent speaker feedback
                if (window.currentSpeechRecognition) {
                    console.log('🔇 STOPPING speech recognition to prevent speaker feedback');
                    window.speechRecognitionPaused = true;
                    window.currentSpeechRecognition.stop();
                    window.currentSpeechRecognition = null;
                }

                // Set lower volume to reduce speaker feedback
                audio.volume = 0.7;

                // Start playback
                audio.play().catch(error => {
                    console.error('Failed to play ElevenLabs audio:', error);
                    URL.revokeObjectURL(audioUrl);
                    window.elevenLabsCurrentAudio = null;
                    window.speechRecognitionPaused = false;
                    reject(error);
                });
            });
        },

        // Session and history management methods
        loadSessionInfo: function() {
            // Initialize session info - no async operations needed here
            console.log('Session info loaded for user:', config.user_id || config.email || 'anonymous');
        },

        loadChatHistory: function() {
            return new Promise((resolve) => {
                // Only load history for identified users
                if (!config.user_id && !config.email && !config.device_id) {
                    resolve(false);
                    return;
                }

                // Skip if persistentHistoryCount is 0 or disabled
                if (!config.persistentHistoryCount || config.persistentHistoryCount <= 0) {
                    resolve(false);
                    return;
                }

                fetch(`${config.apiUrl}/widget_history?user_id=${encodeURIComponent(config.user_id || '')}&email=${encodeURIComponent(config.email || '')}&device_id=${encodeURIComponent(config.device_id || '')}&count=${config.persistentHistoryCount}`, {
                    headers: {
                        'X-Widget-Origin': window.location.origin
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.history && data.history.length > 0) {
                        console.log('Loading chat history:', data.history.length, 'conversations');
                        
                        // Add history messages without storing them again
                        data.history.forEach(item => {
                            this.addMessage(item.question, 'user', false, false); // false = no typing, no store
                            this.addMessage(item.response, 'bot', false, false); // false = no typing, no store
                        });
                        
                        resolve(true);
                    } else {
                        resolve(false);
                    }
                })
                .catch(error => {
                    console.error('Error loading chat history:', error);
                    resolve(false);
                });
            });
        },

        loadChatHistoryOnDemand: function() {
            return new Promise((resolve) => {
                // Same implementation as loadChatHistory but called on demand
                this.loadChatHistory().then((loaded) => {
                    if (loaded) {
                        // Scroll to bottom after loading history
                        setTimeout(() => {
                            this.scrollToBottom();
                        }, 100);
                    }
                    resolve(loaded);
                });
            });
        },

        shouldShowFeedback: function(responseData) {
            // Debug response data structure
            console.log('shouldShowFeedback - responseData:', responseData);
            
            // Show feedback for RAG responses only (knowledge base responses)
            if (!responseData || !responseData.response_type) {
                console.log('shouldShowFeedback - No responseData or response_type:', responseData);
                return false;
            }
            // Check for RAG response types (both old and new format)
            const ragResponseTypes = ['RAG_KNOWLEDGE_BASE', 'rag_with_ai_tools'];
            if (!ragResponseTypes.includes(responseData.response_type)) {
                console.log('shouldShowFeedback - Not RAG response, type:', responseData.response_type);
                return false;
            }
            
            console.log('shouldShowFeedback - RAG response detected, showing feedback buttons');
            // Show feedback buttons for all RAG responses 
            return true;
        },

        addFeedbackButtons: function(messageDiv, text, responseData) {
            console.log('addFeedbackButtons called for:', text.substring(0, 50), 'responseData:', responseData);
            
            // Create feedback container
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-buttons';
            feedbackDiv.style.cssText = 'margin-top: 8px; text-align: center; opacity: 0.7;';

            // Thumbs up button
            const thumbsUpBtn = document.createElement('button');
            thumbsUpBtn.innerHTML = '👍';
            thumbsUpBtn.style.cssText = 'background: none; border: none; font-size: 16px; cursor: pointer; margin: 0 5px; padding: 2px; opacity: 0.6;';
            thumbsUpBtn.title = 'Helpful response';

            // Thumbs down button  
            const thumbsDownBtn = document.createElement('button');
            thumbsDownBtn.innerHTML = '👎';
            thumbsDownBtn.style.cssText = 'background: none; border: none; font-size: 16px; cursor: pointer; margin: 0 5px; padding: 2px; opacity: 0.6;';
            thumbsDownBtn.title = 'Not helpful';

            // Add click handlers
            thumbsUpBtn.onclick = () => this.submitFeedback(text, responseData, 'positive', feedbackDiv);
            thumbsDownBtn.onclick = () => this.submitFeedback(text, responseData, 'negative', feedbackDiv);

            feedbackDiv.appendChild(thumbsUpBtn);
            feedbackDiv.appendChild(thumbsDownBtn);
            
            // Insert feedback buttons before the message
            messageDiv.parentNode.insertBefore(feedbackDiv, messageDiv);
        },

        submitFeedback: function(responseText, responseData, rating, feedbackDiv) {
            // Map rating to feedback_type expected by backend
            const feedbackType = rating === 'positive' ? 'thumbs_up' : 'thumbs_down';
            
            const feedbackData = {
                user_question: responseData.user_question || 'Unknown question',
                bot_response: responseText,
                response_type: responseData.response_type || 'rag',
                feedback_type: feedbackType,
                user_id: config.user_id || null,
                username: config.username || null,
                email: config.email || null,
                session_id: sessionId,
                feedback_comment: '',
                retrieved_chunks: JSON.stringify(responseData.retrieved_chunks || null)
            };

            fetch(`${config.apiUrl}/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify(feedbackData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Remove feedback buttons immediately
                    feedbackDiv.remove();
                    
                    // Add thank you message and close chat confirmation
                    this.addMessage('Thank you for your feedback! Would you like to continue chatting or close this conversation?', 'bot', false);
                    
                    // Add continue/close buttons
                    this.addChatCloseButtons();
                } else {
                    console.error('Feedback submission failed:', data.message);
                }
            })
            .catch(error => {
                console.error('Error submitting feedback:', error);
            });
        },

        addChatCloseButtons: function() {
            const messagesContainer = document.querySelector('.chat-widget-messages');
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'chat-close-buttons';
            buttonContainer.style.cssText = 'text-align: center; margin: 10px 0; padding: 0 10px;';

            const continueBtn = document.createElement('button');
            continueBtn.textContent = 'Continue chatting';
            continueBtn.style.cssText = 'background: #667eea; color: white; border: none; padding: 8px 16px; margin: 0 5px; border-radius: 15px; cursor: pointer; font-size: 12px;';

            const closeBtn = document.createElement('button'); 
            closeBtn.textContent = 'Yes, close chat';
            closeBtn.style.cssText = 'background: #e2e8f0; color: #4a5568; border: none; padding: 8px 16px; margin: 0 5px; border-radius: 15px; cursor: pointer; font-size: 12px;';

            continueBtn.onclick = (e) => {
                console.log('Continue chatting clicked - removing button container only');
                e.preventDefault();
                e.stopPropagation();
                buttonContainer.remove();
                console.log('Button container removed, chat should remain open');
            };

            closeBtn.onclick = () => {
                this.closeWidget();
            };

            buttonContainer.appendChild(continueBtn);
            buttonContainer.appendChild(closeBtn);
            messagesContainer.appendChild(buttonContainer);
            
            this.scrollToBottom();
        },

        updateVoiceControls: function() {
            const voiceBtn = document.querySelector('.chat-widget-voice-btn');
            const elevenLabsBtn = document.querySelector('.chat-widget-elevenlabs-btn');
            
            if (voiceBtn) {
                if (config.continuousVoice) {
                    voiceBtn.innerHTML = '📞'; // Phone icon when in call mode
                    voiceBtn.title = 'Disconnect voice call';
                    voiceBtn.style.backgroundColor = '#ef4444'; // Red background when active
                } else if (isPlayingVoice) {
                    voiceBtn.innerHTML = '🔊'; // Speaker icon when playing
                    voiceBtn.title = 'Stop voice';
                    voiceBtn.style.backgroundColor = '#f59e0b'; // Orange background when playing
                } else {
                    voiceBtn.innerHTML = '🎙️'; // Microphone icon when idle
                    voiceBtn.title = 'Start voice mode';
                    voiceBtn.style.backgroundColor = ''; // Default background
                }
            }
            
            if (elevenLabsBtn) {
                if (config.elevenlabsEmbeddedActive) {
                    elevenLabsBtn.innerHTML = '⚡'; // Lightning bolt when active
                    elevenLabsBtn.title = 'Disconnect ElevenLabs voice agent';
                    elevenLabsBtn.style.backgroundColor = '#ef4444'; // Red background when active
                } else {
                    elevenLabsBtn.innerHTML = '⚡'; // Lightning bolt when idle
                    elevenLabsBtn.title = 'Start ElevenLabs voice agent';
                    elevenLabsBtn.style.backgroundColor = ''; // Default background
                }
            }
        },

        updateElevenLabsEmbeddedControls: function() {
            // Alias for updateVoiceControls to handle ElevenLabs specific updates
            this.updateVoiceControls();
        },

        startContinuousVoiceMode: function() {
            console.log('Starting continuous voice mode');
            config.continuousVoice = true;
            this.updateVoiceControls();
            this.addMessage("📞 Voice call started! I'm listening. Speak naturally and I'll respond. Say 'stop' to end the call.", 'bot', false);
            
            // Start speech recognition
            setTimeout(() => {
                this.startSpeechRecognition();
            }, 1000);
        },

        disconnectVoiceMode: function() {
            console.log('Disconnecting voice mode');
            config.continuousVoice = false;
            
            // Stop current speech recognition
            if (window.currentSpeechRecognition) {
                window.currentSpeechRecognition.stop();
                window.currentSpeechRecognition = null;
            }
            
            // Stop current audio
            this.stopVoice();
            
            this.updateVoiceControls();
            this.addMessage("📞 Voice call ended. You can continue chatting with text or start a new voice call.", 'bot', false);
        },

        stopVoice: function() {
            console.log('Stopping voice');
            
            // Stop current audio playback
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                currentAudio = null;
            }
            
            // Stop ElevenLabs audio
            if (window.elevenLabsCurrentAudio) {
                window.elevenLabsCurrentAudio.pause();
                window.elevenLabsCurrentAudio.currentTime = 0;
                window.elevenLabsCurrentAudio = null;
            }
            
            isPlayingVoice = false;
            window.speechRecognitionPaused = false;
            this.updateVoiceControls();
        },

        startSpeechRecognition: function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                console.warn('Speech recognition not supported');
                return;
            }

            // Don't start if already active or paused
            if (window.currentSpeechRecognition || window.speechRecognitionPaused) {
                return;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-IN'; // Indian English

            let finalTranscript = '';
            let silenceTimer = null;

            recognition.onstart = () => {
                console.log('Speech recognition started');
                window.currentSpeechRecognition = recognition;
            };

            recognition.onresult = (event) => {
                let interimTranscript = '';
                finalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                // Handle voice commands
                const command = (finalTranscript + interimTranscript).trim().toLowerCase();
                
                // Check for stop commands
                if (command.includes('stop') || command.includes('pause') || command.includes('end call')) {
                    recognition.stop();
                    this.disconnectVoiceMode();
                    return;
                }
                
                // Process final transcript
                if (finalTranscript.trim()) {
                    console.log('Voice input:', finalTranscript);
                    
                    // Send the voice input as a message
                    const inputField = document.querySelector('.chat-widget-input');
                    if (inputField) {
                        inputField.value = finalTranscript.trim();
                        this.sendMessage();
                    }
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                window.currentSpeechRecognition = null;
                
                // Restart recognition for certain errors
                if (config.continuousVoice && event.error !== 'aborted') {
                    setTimeout(() => {
                        this.startSpeechRecognition();
                    }, 2000);
                }
            };

            recognition.onend = () => {
                console.log('Speech recognition ended');
                window.currentSpeechRecognition = null;
                
                // Restart recognition if still in continuous mode
                if (config.continuousVoice && !window.speechRecognitionPaused) {
                    setTimeout(() => {
                        this.startSpeechRecognition();
                    }, 1000);
                }
            };

            recognition.start();
        },

        addBotMessage: function(message) {
            // Alias for addMessage with bot sender
            this.addMessage(message, 'bot', false);
        },

        isRAGResponse: function(responseData) {
            // Check if the response is from RAG knowledge base
            if (!responseData) return false;
            return responseData.response_type === 'RAG_KNOWLEDGE_BASE';
        },

        updateSessionInfo: function(userInfo) {
            // Update session information with user data
            if (userInfo) {
                if (userInfo.user_id) config.user_id = userInfo.user_id;
                if (userInfo.username) config.username = userInfo.username;
                if (userInfo.email) config.email = userInfo.email;
                console.log('Session info updated:', userInfo);
            }
        },

        loadCustomIcon: function() {
            return new Promise((resolve) => {
                // Try to load custom icon directly from static path
                const iconPath = `${config.apiUrl}/static/widget_icons/widget_icon.png`;
                
                // Create a test image to check if icon exists
                const testImg = new Image();
                testImg.onload = () => {
                    config.iconUrl = iconPath;
                    console.log('Custom icon loaded from:', iconPath);
                    resolve();
                };
                testImg.onerror = () => {
                    console.log('No custom icon found, using default');
                    resolve();
                };
                testImg.src = iconPath;
            });
        },

        sanitizeInput: function(input) {
            // Basic input sanitization
            if (typeof input !== 'string') return input;
            return input.replace(/<script[^>]*>.*?<\/script>/gi, '')
                       .replace(/<[^>]*>/g, '')
                       .trim()
                       .substring(0, 500); // Limit length
        },

        clearConversation: function() {
            // Clear the chat messages
            const messagesContainer = document.querySelector('.chat-widget-messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
            }
            
            // Reset conversation count
            conversationCount = 0;
            
            // Generate new session ID
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            
            // Update session info display
            this.updateSessionInfo();
            
            // Show welcome message again
            if (config.welcomeMessage) {
                const welcomeMsg = this.getPersonalizedWelcome();
                this.addMessage(welcomeMsg, 'bot');
            }
            
            // Clear memory on server side
            this.clearMemory();
        },

        clearMemory: function() {
            fetch(`${config.apiUrl}/clear_memory`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_id: config.user_id,
                    email: config.email,
                    device_id: config.device_id
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Memory cleared:', data);
            })
            .catch(error => {
                console.error('Error clearing memory:', error);
            });
        },

        // All legacy ElevenLabs API functions removed - now using embedded agent

    };

    // Removed all live chat functionality - pure chatbot RAG only

    // Global object
    window.ChatWidget = ChatWidget;

    // Auto-initialize if config is provided
    if (window.chatWidgetConfig) {
        ChatWidget.init(window.chatWidgetConfig);
    }

})();