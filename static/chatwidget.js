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
        timeBasedGreeting: true // Show time-based greeting for first-time users
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
                <button class="chat-widget-close">×</button>
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

            // Clear button
            chatWindow.querySelector('.chat-widget-clear-btn').addEventListener('click', () => {
                this.clearConversation();
            });

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
                    
                    // Track RAG responses for feedback timing
                    const responseData = { ...response, user_question: sanitizedMessage };
                    if (this.isRAGResponse(responseData)) {
                        this.trackRAGResponse();
                    }
                    
                    // Pass the full response data and the user question for feedback
                    this.addMessage(response.answer, 'bot', false, true, true, responseData); // Enable typing effect with response data
                    this.updateSessionInfo(response.user_info);
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
                timestamp: Date.now()
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

        loadChatHistory: function() {
            // Only load history if user identification is available
            if (!config.user_id && !config.email && !config.device_id) {
                return Promise.resolve(false);
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                limit: config.persistentHistoryCount
            };

            return fetch(`${config.apiUrl}/widget_history`, {
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
                console.log('Widget history loaded:', data);
                if (data.history && Array.isArray(data.history) && data.history.length > 0) {
                    console.log(`Loading ${data.history.length} messages from history`);
                    // Load messages without typing effect and without storing in history again
                    // History comes in chronological order (oldest first), so we can use it directly
                    data.history.forEach((message, index) => {
                        console.log('Loading message:', message);
                        this.addMessage(message.content, message.role === 'user' ? 'user' : 'bot', false, false, false);
                        // Scroll to bottom after each message to ensure proper positioning
                        if (index === data.history.length - 1) {
                            setTimeout(() => this.scrollToBottom(), 50);
                        }
                    });
                    
                    // Scroll to bottom after loading history
                    if (data.history.length > 0) {
                        this.scrollToBottom();
                    }
                    
                    return true; // History was loaded
                } else {
                    return false; // No history found
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                return false; // Return false on error
            });
        },

        loadChatHistoryOnDemand: function() {
            // Only load history if user identification is available
            if (!config.user_id && !config.email && !config.device_id) {
                return Promise.resolve(false);
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id,
                limit: config.persistentHistoryCount
            };

            return fetch(`${config.apiUrl}/widget_history`, {
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
                console.log('Widget history loaded on demand:', data);
                if (data.history && Array.isArray(data.history) && data.history.length > 0) {
                    console.log(`Loading ${data.history.length} messages from history`);
                    
                    // Insert history messages BEFORE the welcome message in correct chronological order
                    const welcomeMessage = messagesContainer.querySelector('.chat-widget-message.bot');
                    
                    // History comes in chronological order, but we need to insert them in reverse
                    // so the oldest appears first when we insert before the welcome message
                    const insertionPoint = welcomeMessage;
                    
                    // Insert messages in reverse order so they appear chronologically correct
                    for (let i = data.history.length - 1; i >= 0; i--) {
                        const message = data.history[i];
                        console.log('Loading message:', message);
                        const messageDiv = document.createElement('div');
                        messageDiv.className = `chat-widget-message ${message.role === 'user' ? 'user' : 'bot'}`;
                        
                        const bubble = document.createElement('div');
                        bubble.className = 'chat-widget-message-bubble';
                        bubble.innerHTML = this.formatMessage(message.content, message.role === 'user');
                        
                        messageDiv.appendChild(bubble);
                        
                        // Insert before welcome message
                        if (insertionPoint) {
                            messagesContainer.insertBefore(messageDiv, insertionPoint);
                        } else {
                            messagesContainer.appendChild(messageDiv);
                        }
                    }
                    
                    // Scroll to bottom after loading history
                    setTimeout(() => this.scrollToBottom(), 100);
                    
                    return true; // History was loaded
                } else {
                    console.log('No history found');
                    return false; // No history found
                }
            })
            .catch(error => {
                console.error('Error loading chat history on demand:', error);
                return false; // Return false on error
            });
        },

        loadSessionInfo: function() {
            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id
            };

            const options = {
                method: (config.user_id || config.email || config.device_id) ? 'POST' : 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (options.method === 'POST') {
                options.body = JSON.stringify(payload);
            }

            fetch(`${config.apiUrl}/session_info`, options)
                .then(response => response.json())
                .then(data => {
                    this.updateSessionInfo(data);
                })
                .catch(error => {
                    console.error('Error loading session info:', error);
                });
        },

        updateSessionInfo: function(data) {
            const sessionInfoEl = chatWindow.querySelector('.session-type');
            if (data && data.session_type) {
                const sessionType = data.session_type === 'persistent' ? 'Logged in' : 'Guest';
                const messageCount = data.stats ? data.stats.total_messages : 0;
                sessionInfoEl.textContent = `${sessionType} • ${messageCount} messages`;
            } else {
                sessionInfoEl.textContent = 'Guest • 0 messages';
            }
        },

        clearConversation: function() {
            if (!confirm('Are you sure you want to clear the conversation?')) {
                return;
            }

            const payload = {
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                device_id: config.device_id
            };

            fetch(`${config.apiUrl}/clear_session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            }).then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Clear UI
                        messagesContainer.innerHTML = '';
                        conversationHistory = [];
                        ragResponseCount = 0; // Reset RAG response count for feedback timing
                        
                        // Add welcome message
                        if (config.welcomeMessage) {
                            this.addMessage(config.welcomeMessage, 'bot');
                        }
                        
                        // Update session info
                        this.loadSessionInfo();
                    }
                })
                .catch(error => {
                    console.error('Error clearing conversation:', error);
                });
        },

        // Public methods
        destroy: function() {
            if (widgetContainer && widgetContainer.parentNode) {
                widgetContainer.parentNode.removeChild(widgetContainer);
            }
            isInitialized = false;
            isOpen = false;
        },

        updateConfig: function(newConfig) {
            config = { ...config, ...newConfig };
            this.loadSessionInfo();
        },

        // ===========================
        // FEEDBACK FUNCTIONALITY
        // ===========================
        
        isRAGResponse: function(responseData) {
            // Check if this is a RAG response based on response_type
            return responseData && responseData.response_type && 
                   (responseData.response_type.includes('rag') || 
                    responseData.response_type === 'rag_with_ai_tools' ||
                    responseData.response_type === 'rag_with_memory');
        },

        shouldShowFeedback: function(responseData) {
            // Only show feedback for RAG responses after 3+ conversations
            // OR if the user said "thank you" (check if response includes appreciation)
            if (!this.isRAGResponse(responseData)) {
                return false;
            }
            
            // Check if this is a simple greeting/small talk (exclude these from feedback)
            const userMessage = responseData.user_question ? responseData.user_question.toLowerCase().trim() : '';
            const botResponse = responseData.answer ? responseData.answer.toLowerCase() : '';
            
            // Simple greetings that shouldn't get feedback
            const simpleGreetings = ['hi', 'hello', 'hey', 'how are you', 'good morning', 'good afternoon', 'good evening'];
            const isSimpleGreeting = simpleGreetings.some(greeting => 
                userMessage === greeting || userMessage.includes(greeting)
            );
            
            // Simple bot responses that shouldn't get feedback
            const isSimpleBotResponse = botResponse.length < 50 && (
                botResponse.includes('how can i help') ||
                botResponse.includes('what can i help') ||
                botResponse.includes('hey!') ||
                botResponse.includes('hello!') ||
                botResponse.includes('hi!')
            );
            
            // Skip feedback for simple greetings/responses
            if (isSimpleGreeting || isSimpleBotResponse) {
                return false;
            }
            
            // Check if this is a thank you response (user saying thanks/goodbye)
            const isThankYouMessage = userMessage.includes('thank') || 
                                      userMessage.includes('thanks') || 
                                      userMessage.includes('bye') || 
                                      userMessage.includes('goodbye') ||
                                      userMessage.includes('that\'s all') ||
                                      userMessage.includes('thats all');
            
            // Show feedback if it's 3+ conversations OR if user is saying thanks/goodbye
            return ragResponseCount >= 3 || isThankYouMessage;
        },

        trackRAGResponse: function() {
            // Increment RAG response count (called when a new RAG response is received)
            ragResponseCount++;
        },

        addFeedbackButtons: function(messageDiv, botResponse, responseData) {
            // Only add feedback buttons once
            if (messageDiv.querySelector('.feedback-container')) {
                return;
            }

            const feedbackContainer = document.createElement('div');
            feedbackContainer.className = 'feedback-container';
            feedbackContainer.style.cssText = `
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 6px;
                padding: 2px 0;
                opacity: 0.7;
            `;

            // Thumbs up button
            const thumbsUpBtn = document.createElement('button');
            thumbsUpBtn.className = 'feedback-btn thumbs-up';
            thumbsUpBtn.innerHTML = '👍';
            thumbsUpBtn.title = 'This answer was helpful';
            thumbsUpBtn.style.cssText = `
                background: none;
                border: 1px solid #e0e0e0;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-size: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                opacity: 0.8;
            `;

            // Thumbs down button
            const thumbsDownBtn = document.createElement('button');
            thumbsDownBtn.className = 'feedback-btn thumbs-down';
            thumbsDownBtn.innerHTML = '👎';
            thumbsDownBtn.title = 'This answer needs improvement';
            thumbsDownBtn.style.cssText = thumbsUpBtn.style.cssText;

            // Add feedback buttons
            feedbackContainer.appendChild(thumbsUpBtn);
            feedbackContainer.appendChild(thumbsDownBtn);
            
            // Insert BEFORE the message card, not after
            messageDiv.parentNode.insertBefore(feedbackContainer, messageDiv);

            // Event listeners
            thumbsUpBtn.addEventListener('click', () => {
                this.submitFeedback('thumbs_up', botResponse, responseData, feedbackContainer, messageDiv);
            });

            thumbsDownBtn.addEventListener('click', () => {
                this.submitFeedback('thumbs_down', botResponse, responseData, feedbackContainer, messageDiv);
            });

            // Hover effects
            [thumbsUpBtn, thumbsDownBtn].forEach(btn => {
                btn.addEventListener('mouseenter', () => {
                    btn.style.backgroundColor = '#f5f5f5';
                    btn.style.borderColor = '#ccc';
                });
                btn.addEventListener('mouseleave', () => {
                    btn.style.backgroundColor = 'transparent';
                    btn.style.borderColor = '#e0e0e0';
                });
            });
        },

        submitFeedback: function(feedbackType, botResponse, responseData, feedbackContainer, messageDiv) {
            const feedbackData = {
                session_id: sessionId,
                user_id: config.user_id,
                username: config.username,
                email: config.email,
                user_question: responseData.user_question,
                bot_response: botResponse,
                response_type: responseData.response_type || 'rag',
                feedback_type: feedbackType,
                feedback_comment: '', // Could be extended to include user comments
                retrieved_chunks: responseData.retrieved_chunks || null
            };

            // Remove the feedback buttons immediately
            feedbackContainer.remove();

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
                    // Add thank you message as a new bot message
                    const thankYouText = feedbackType === 'thumbs_up' ? 
                        'Thank you for the feedback! 😊 Would you like to close this chat?' : 
                        'Thank you for the feedback! We\'ll work on improving this. Would you like to close this chat?';
                    
                    this.addThankYouMessage(thankYouText);
                } else {
                    // Add error message as bot message
                    this.addMessage('Failed to submit feedback. Please try again.', 'bot', true);
                }
            })
            .catch(error => {
                console.error('Error submitting feedback:', error);
                this.addMessage('Error submitting feedback. Please try again.', 'bot', true);
            });
        },

        addThankYouMessage: function(thankYouText) {
            // Add the thank you message first
            this.addMessage(thankYouText, 'bot', true);
            
            // Then add a separate message with the action buttons
            const actionMessageDiv = document.createElement('div');
            actionMessageDiv.className = 'chat-widget-message bot-message';
            actionMessageDiv.style.cssText = `
                display: flex;
                justify-content: flex-start;
                margin-bottom: 12px;
                align-items: flex-end;
            `;
            
            const actionBubble = document.createElement('div');
            actionBubble.className = 'chat-widget-bubble';
            actionBubble.style.cssText = `
                background: #f1f1f1;
                color: #333;
                padding: 8px 12px;
                border-radius: 18px;
                max-width: 80%;
                word-wrap: break-word;
                font-size: 14px;
                line-height: 1.4;
            `;

            // Add close chat confirmation buttons
            const actionContainer = document.createElement('div');
            actionContainer.style.cssText = `
                display: flex;
                gap: 8px;
                align-items: center;
            `;

            const yesBtn = document.createElement('button');
            yesBtn.innerHTML = 'Yes, close chat';
            yesBtn.style.cssText = `
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                cursor: pointer;
                transition: background-color 0.2s;
            `;

            const noBtn = document.createElement('button');
            noBtn.innerHTML = 'Continue chatting';
            noBtn.style.cssText = `
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                cursor: pointer;
                transition: background-color 0.2s;
            `;

            // Event listeners
            yesBtn.addEventListener('click', () => {
                this.closeWidget();
            });

            noBtn.addEventListener('click', () => {
                // Remove the action buttons and replace with "Happy to help!" message
                actionContainer.innerHTML = '<span style="color: #666; font-size: 12px; font-style: italic;">Happy to help! 😊</span>';
            });

            // Hover effects
            yesBtn.addEventListener('mouseenter', () => yesBtn.style.backgroundColor = '#c82333');
            yesBtn.addEventListener('mouseleave', () => yesBtn.style.backgroundColor = '#dc3545');
            noBtn.addEventListener('mouseenter', () => noBtn.style.backgroundColor = '#218838');
            noBtn.addEventListener('mouseleave', () => noBtn.style.backgroundColor = '#28a745');

            actionContainer.appendChild(yesBtn);
            actionContainer.appendChild(noBtn);
            actionBubble.appendChild(actionContainer);
            actionMessageDiv.appendChild(actionBubble);
            
            // Add to messages container
            messagesContainer.appendChild(actionMessageDiv);
            this.scrollToBottom();
        },

        closeWidget: function() {
            // Close the widget
            if (isOpen) {
                this.toggle();
            }
        },

        showThankYouFlow: function(feedbackContainer, feedbackType) {
            // Replace feedback buttons with thank you message and close option
            feedbackContainer.innerHTML = '';
            feedbackContainer.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin-top: 8px;
                padding: 8px 12px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            `;

            // Thank you message
            const thankYouText = document.createElement('div');
            thankYouText.style.cssText = `
                font-size: 12px;
                color: #28a745;
                font-weight: 500;
                margin-bottom: 4px;
            `;
            thankYouText.innerHTML = feedbackType === 'thumbs_up' ? 
                '✓ Thank you! Your feedback helps us improve.' : 
                '✓ Thank you for your feedback. We\'ll work on improving this.';

            // Close chat option
            const closeOption = document.createElement('div');
            closeOption.style.cssText = `
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 11px;
                color: #666;
            `;

            const closeBtn = document.createElement('button');
            closeBtn.textContent = 'Close Chat';
            closeBtn.style.cssText = `
                background: #007bff;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 11px;
                transition: background 0.2s;
            `;

            closeBtn.addEventListener('click', () => {
                this.toggle(); // Close the chat widget
            });

            closeBtn.addEventListener('mouseenter', () => {
                closeBtn.style.backgroundColor = '#0056b3';
            });
            closeBtn.addEventListener('mouseleave', () => {
                closeBtn.style.backgroundColor = '#007bff';
            });

            const continueText = document.createElement('span');
            continueText.textContent = 'or continue chatting';

            closeOption.appendChild(closeBtn);
            closeOption.appendChild(continueText);

            feedbackContainer.appendChild(thankYouText);
            feedbackContainer.appendChild(closeOption);

            // Auto-hide after 15 seconds
            setTimeout(() => {
                if (feedbackContainer.parentNode) {
                    feedbackContainer.style.opacity = '0.5';
                    feedbackContainer.style.pointerEvents = 'none';
                }
            }, 15000);
        }
    };



    // Add live chat properties and methods to ChatWidget
    let isLiveChatActive = false;
    let liveChatSessionId = null;
    let processedMessages = new Set();
    let liveChatPollingInterval = null;

    // Live chat methods
    const liveChatMethods = {
        initializeLiveChat: function() {
            isLiveChatActive = false;
            liveChatSessionId = null;
            processedMessages = new Set();
            liveChatPollingInterval = null;
        },

        startLiveChatPolling: function() {
            if (liveChatPollingInterval) {
                clearInterval(liveChatPollingInterval);
            }

            liveChatPollingInterval = setInterval(() => {
                if (isLiveChatActive && liveChatSessionId) {
                    liveChatMethods.pollLiveChatMessages();
                }
            }, 3000);
        },

        pollLiveChatMessages: function() {
            if (!liveChatSessionId) return;

            fetch(`${config.apiUrl}/api/live_chat/sessions/${liveChatSessionId}/messages`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.messages) {
                    data.messages.forEach(message => {
                        if (message.sender_type === 'agent' && !processedMessages.has(message.message_id)) {
                            ChatWidget.addMessage(message.message_content, 'bot');
                            processedMessages.add(message.message_id);
                            
                            const inputField = document.querySelector('.chat-widget-input');
                            if (inputField) {
                                inputField.placeholder = `Connected to ${message.sender_name || 'Agent'}. Type your message...`;
                            }
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error polling live chat messages:', error);
            });
        },

        sendLiveChatMessage: function(message) {
            if (!isLiveChatActive || !liveChatSessionId) {
                return Promise.reject('Live chat not active');
            }

            const messageData = {
                sender_type: 'user',
                sender_id: config.user_id || config.email || config.device_id || 'anonymous',
                sender_name: config.username || 'User',
                message_content: message,
                message_type: 'text'
            };

            return fetch(`${config.apiUrl}/api/live_chat/sessions/${liveChatSessionId}/send_message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify(messageData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Live chat message sent successfully');
                } else {
                    console.error('Error sending live chat message:', data.error);
                }
                return data;
            });
        },

        transferToAgent: function(reason) {
            const transferData = {
                user_identifier: config.user_id || config.email || config.device_id || 'anonymous',
                username: config.username,
                email: config.email,
                initial_message: reason || 'User requested live agent assistance',
                department: config.department || 'support',
                priority: config.priority || 'normal'
            };

            return fetch(`${config.apiUrl}/api/live_chat/transfer_to_agent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Widget-Origin': window.location.origin
                },
                body: JSON.stringify(transferData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    isLiveChatActive = true;
                    liveChatSessionId = data.session_id;
                    
                    // Add system message about transfer
                    ChatWidget.addMessage(data.message, 'bot');
                    
                    // Start polling for agent messages
                    liveChatMethods.startLiveChatPolling();
                    
                    // Update input placeholder
                    const inputField = document.querySelector('.chat-widget-input');
                    if (inputField) {
                        inputField.placeholder = 'Waiting for agent... Type your message here';
                    }
                    
                    console.log('Successfully transferred to live agent');
                } else {
                    console.error('Error transferring to agent:', data.error);
                    ChatWidget.addMessage('Sorry, live chat is currently unavailable. Please try again later.', 'bot');
                }
                return data;
            })
            .catch(error => {
                console.error('Error transferring to agent:', error);
                ChatWidget.addMessage('Sorry, there was an error connecting to live chat. Please try again later.', 'bot');
                return { success: false, error: error.message };
            });
        }
    };



    // Modify the existing sendMessage to add live chat functionality
    const originalSendMessage = ChatWidget.sendMessage;
    ChatWidget.sendMessage = function() {
        const message = inputField.value.trim();
        if (!message) return;

        // Check if user wants to transfer to live chat
        const liveChatKeywords = ['live chat', 'chat with agent', 'talk to agent', 'human agent', 'speak to human', 'connect to agent'];
        const messageText = message.toLowerCase();
        const requestsLiveChat = liveChatKeywords.some(keyword => messageText.includes(keyword));

        if (requestsLiveChat && !isLiveChatActive) {
            // Add user message first
            ChatWidget.addMessage(message, 'user');
            inputField.value = '';
            
            // Then transfer to agent
            liveChatMethods.transferToAgent(`User requested: ${message}`);
            return;
        }

        if (isLiveChatActive) {
            // Add user message 
            ChatWidget.addMessage(message, 'user');
            inputField.value = '';
            
            // Send to live chat
            liveChatMethods.sendLiveChatMessage(message).catch(error => {
                console.error('Error sending live chat message:', error);
                ChatWidget.addMessage('Sorry, there was an error sending your message. Please try again.', 'bot');
            });
        } else {
            // Use original AI/RAG functionality for regular messages
            originalSendMessage.call(this);
        }
    };

    // Initialize live chat when widget is created
    const originalInitializeWidget = ChatWidget.initializeWidget;
    ChatWidget.initializeWidget = function() {
        originalInitializeWidget.call(this);
        liveChatMethods.initializeLiveChat();
        
        // Make transfer function globally accessible
        window.transferToAgent = function(reason) {
            liveChatMethods.transferToAgent(reason);
        };
    };

    // Global object
    window.ChatWidget = ChatWidget;

    // Auto-initialize if config is provided
    if (window.chatWidgetConfig) {
        ChatWidget.init(window.chatWidgetConfig);
    }

})();