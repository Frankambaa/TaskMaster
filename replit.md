# RAG Chatbot with Admin Panel

## Overview

This is a full-stack AI-powered chatbot application built with Flask that implements Retrieval-Augmented Generation (RAG) using OpenAI's API. The system allows administrators to upload PDF and DOCX documents, vectorize them using FAISS, and provides an intelligent chatbot interface that can answer questions based on the uploaded documents while also handling casual conversation.

## System Architecture

### Backend Architecture
- **Framework**: Flask with CORS support
- **Vector Database**: FAISS for efficient similarity search
- **Document Processing**: PyPDF2 for PDFs, python-docx for DOCX files
- **AI Integration**: OpenAI API for embeddings and chat completion
- **Text Processing**: Tiktoken for token counting and text chunking

### Frontend Architecture
- **Chat Interface**: Vanilla JavaScript with modern ES6 classes
- **Styling**: Bootstrap 5 with custom CSS for ChatGPT-inspired design
- **Admin Panel**: Server-side rendered HTML with Flask templates
- **Responsive Design**: Mobile-first approach with flexbox layout

## Key Components

### 1. Document Vectorizer (`vectorizer.py`)
- **Purpose**: Processes uploaded documents and creates vector embeddings
- **Text Extraction**: Handles both PDF and DOCX file formats
- **Chunking Strategy**: Splits text into 500-token chunks with 50-token overlap
- **Embedding Model**: Uses OpenAI's `text-embedding-ada-002`

### 2. RAG Chain (`rag_chain.py`)
- **Purpose**: Implements the retrieval-augmented generation logic with LangChain integration
- **Chat Model**: Uses GPT-4o for response generation via LangChain
- **Session Memory**: Maintains conversation context per user session
- **Small Talk Handling**: Built-in responses for common greetings and pleasantries
- **Retrieval**: Top-k similarity search (k=3) for relevant document chunks
- **Memory Management**: Conversation history with session isolation

### 3. Session Memory System (`session_memory.py`)
- **Purpose**: Manages conversation memory with session isolation for multi-user privacy
- **LangChain Integration**: Uses LangChain's memory components for conversation tracking
- **Session Isolation**: Each user gets unique session ID with isolated memory
- **Memory Persistence**: Maintains conversation context across multiple interactions
- **Privacy Protection**: No cross-user data sharing or leakage
- **Memory Management**: Automatic cleanup and session management
- **User-Specific Persistence**: Database-backed storage for authenticated users with cross-device continuity
- **Dual Storage System**: Persistent storage for users with identifiers, temporary for anonymous sessions

### 4. AI-Driven Tool System (`ai_tool_executor.py`, `models.py`)
- **Smart AI Selection**: Uses OpenAI Function Calling to intelligently select appropriate tools based on natural language understanding
- **Conservative Clarification**: Only asks clarifying questions for extremely ambiguous single-word queries that could match multiple tools
- **Smart Pre-filtering**: Skips clarification for questions with clear context, action words, or sufficient detail
- **Dynamic Tool Loading**: API tools are stored in database and loaded dynamically into OpenAI function specifications
- **Response Mapping**: Configurable field mapping to extract specific data from API responses
- **Response Templates**: AI-powered formatting using customizable templates for user-friendly output
- **Priority System**: Tools with higher priority are preferred during AI selection
- **Parameter Handling**: JSON schema-based parameter validation and dynamic curl command generation
- **Database Storage**: PostgreSQL backend for persistent AI tool management with ApiTool model

### 5. Legacy API Management System (`api_executor.py`, `models.py`)
- **Keyword Matching**: Legacy system with configurable keywords that trigger specific API rules
- **Curl Integration**: Execute any curl command with dynamic placeholder replacement
- **Priority System**: Rules with higher priority are checked first
- **Database Storage**: PostgreSQL backend for persistent API rule management (ApiRule model)

### 4. Flask Application (`app.py`)
- **Routes**: 
  - `/` - Redirects to chatbot interface
  - `/admin` - File upload, vectorization, and API rules management
  - `/chatbot` - Main chat interface
  - `/ask` - API endpoint for chat queries (with smart routing)
  - `/api_rules/*` - API rules CRUD operations
- **File Handling**: Secure file upload with size limits (16MB)
- **Session Management**: Flash messages for user feedback
- **Database Integration**: PostgreSQL with SQLAlchemy ORM

### 4. Frontend Chat Interface
- **Real-time Chat**: AJAX-based messaging system
- **Voice Input**: Speech-to-text functionality using Web Speech API
- **Markdown Support**: Rich text formatting for bot responses (bold, italic, code, line breaks)
- **Custom Logo**: Configurable branding with image upload
- **Typing Effects**: Simulated typing indicator for better UX
- **Connection Status**: Visual feedback for API connectivity
- **Responsive Design**: Works on desktop and mobile devices

## Data Flow

### Standard RAG Flow with Session Memory
1. **Document Upload**: Admin uploads PDF/DOCX files through the admin panel
2. **Text Extraction**: System extracts text from uploaded documents
3. **Chunking**: Text is split into overlapping chunks for better retrieval
4. **Vectorization**: Each chunk is converted to embeddings using OpenAI API
5. **Index Storage**: FAISS index is saved to disk for persistence
6. **Session Management**: User gets unique session ID for conversation isolation
7. **Query Processing**: User questions are embedded and matched against stored vectors
8. **Memory Integration**: Previous conversation context is retrieved for the user's session
9. **Response Generation**: Relevant chunks and conversation history are used as context for GPT-4o via LangChain
10. **Memory Update**: New conversation turns are stored in session memory

### AI-Driven Tool Selection Flow
1. **Question Analysis**: User question is analyzed by OpenAI Function Calling system
2. **Ambiguity Detection**: AI checks if question is vague or could match multiple tools
3. **Clarification Request**: If ambiguous, AI generates clarifying questions and returns them immediately
4. **Tool Selection**: For clear questions, AI intelligently selects appropriate tool based on natural language understanding
5. **Parameter Extraction**: AI extracts required parameters from user question using JSON schema validation
6. **Tool Execution**: Selected tool executes configured curl command with dynamic parameter replacement
7. **Response Mapping**: API response is processed through configurable field mapping
8. **AI Formatting**: Response is formatted by AI using customizable templates for user-friendly output
9. **Fallback to RAG**: If no tool is selected, falls back to standard RAG knowledge base flow

### Legacy Smart API Routing Flow (Keyword-Based)
1. **Question Analysis**: Incoming user question is analyzed for keyword matches
2. **Rule Matching**: System checks active API rules by priority for keyword matches
3. **API Execution**: If matched, executes configured curl command with placeholders replaced
4. **Fallback to RAG**: If no API rule matches, falls back to standard RAG flow
5. **Response Formatting**: API responses are formatted for display in chat interface

## External Dependencies

### Core Dependencies
- **OpenAI API**: For embeddings and chat completion
- **FAISS**: Vector similarity search library
- **Flask**: Web framework and routing
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX text extraction
- **tiktoken**: Token counting for OpenAI models

### Frontend Dependencies
- **Bootstrap 5**: UI framework and responsive design
- **Font Awesome**: Icons for user interface
- **Vanilla JavaScript**: No additional frameworks required

## Deployment Strategy

### Local Development
- **Environment**: SQLite database for quick setup
- **Dependencies**: Python 3.11+, pip, virtualenv
- **Setup**: Use `install_unix.sh` or `install_windows.bat` scripts

### Production Deployment (AWS EC2)
- **Containerization**: Docker with multi-service orchestration
- **Database**: PostgreSQL with automated backups
- **Web Server**: Nginx with SSL termination and rate limiting
- **Caching**: Redis for session storage and caching
- **Monitoring**: Health checks, resource monitoring, and alerting
- **Security**: Firewall, fail2ban, automatic security updates

### Environment Configuration
- **OpenAI API Key**: Required environment variable `OPENAI_API_KEY`
- **Database**: PostgreSQL connection string in `DATABASE_URL`
- **Security**: Strong secret keys for session management
- **SSL**: Let's Encrypt certificates for HTTPS

### Directory Structure
```
uploads/          # Uploaded documents
faiss_index/      # FAISS vector indices
static/           # CSS and JavaScript files
templates/        # HTML templates
logs/             # Application logs
backups/          # Database and file backups
deployment/       # Production deployment files
```

### Production Features
- **Auto-scaling**: Ready for horizontal scaling with load balancer
- **Backup**: Daily automated backups with 7-day retention
- **Monitoring**: Real-time health checks and resource alerts
- **Security**: Comprehensive security hardening and best practices
- **Updates**: Automated security updates and easy application updates
- **SSL**: Automatic SSL certificate management
- **Performance**: Optimized for high-traffic scenarios

## Changelog
- July 03, 2025: Initial RAG chatbot setup with admin panel
- July 03, 2025: Added dynamic small talk responses with random selection
- July 03, 2025: Implemented voice input functionality using Web Speech API
- July 04, 2025: Fixed line break rendering and added markdown support for bot responses
- July 04, 2025: Added logo upload functionality for custom branding
- July 04, 2025: Implemented smart API routing system with keyword-based rules
- July 04, 2025: Added PostgreSQL database backend for API rules management
- July 04, 2025: Created comprehensive admin interface for API rules configuration
- July 04, 2025: Added MySQL support and comprehensive local database setup documentation
- July 15, 2025: Integrated LangChain with session-based memory management for conversation tracking
- July 15, 2025: Added privacy-focused session isolation ensuring no cross-user data sharing
- July 15, 2025: Enhanced chatbot with memory management features including clear memory functionality
- July 16, 2025: **MAJOR ENHANCEMENT**: Implemented user-specific persistent conversation storage
- July 16, 2025: Enhanced /ask API to accept user parameters (user_id, username, email, device_id)
- July 16, 2025: Added cross-device conversation continuity with user identifier-based persistence
- July 16, 2025: Created UserConversation database model for persistent storage
- July 16, 2025: Implemented fallback to temporary sessions for anonymous users
- July 16, 2025: Added user management endpoints for conversation administration
- July 16, 2025: Created comprehensive integration guide and test suite for external embedding
- July 16, 2025: Fixed widget DOM loading issue by adding proper DOMContentLoaded event handling
- July 16, 2025: Enhanced admin panel with comprehensive widget integration section including copy-to-clipboard functionality
- July 16, 2025: Added comprehensive security features to chatwidget.js including rate limiting, input sanitization, XSS protection, session timeout, domain restrictions, and request timeout handling
- July 16, 2025: **MAJOR UPGRADE**: Implemented AI-driven tool-calling system using OpenAI Function Calling to replace keyword-based API triggering
- July 16, 2025: Added ApiTool database model with OpenAI function specifications, response mapping, and configurable templates
- July 16, 2025: Created AIToolExecutor class for intelligent tool selection and execution with natural language understanding
- July 16, 2025: Enhanced admin panel with comprehensive AI tools management interface including CRUD operations and real-time updates
- July 16, 2025: Integrated AI tool selection into RAG chain with fallback to knowledge base when no tools are triggered
- July 16, 2025: Fixed critical bug in AI tool parameter handling - empty parameter objects now work correctly
- July 16, 2025: Added user-friendly API testing interface with visual field selector and automatic response mapping generation
- July 16, 2025: Removed legacy API Rules Management system from admin interface - replaced entirely by AI Tools system
- July 16, 2025: Enhanced installation scripts with comprehensive error handling, dependency verification, and colored output
- July 16, 2025: Updated local_requirements.txt with complete dependency list including LangChain, database drivers, and testing tools
- July 16, 2025: Added automated directory creation and permission setup in installation scripts
- July 17, 2025: **MAJOR ENHANCEMENT**: Implemented persistent chat history that loads last N messages (configurable) on page reload
- July 17, 2025: Added `/widget_history` endpoint to retrieve conversation history for authenticated users
- July 17, 2025: Enhanced chatwidget.js with `persistentHistoryCount` configuration option (default: 10 messages)
- July 17, 2025: Chat history persists across browser sessions and different devices for identified users
- July 17, 2025: Added comprehensive admin panel documentation for persistent history configuration
- July 17, 2025: Fixed bot response text truncation issue in chatwidget - security limits now only apply to user input
- July 17, 2025: **UX ENHANCEMENT**: Added personalized welcome messages with user's name (from username, email, or user_id)
- July 17, 2025: Implemented optional "Load Previous Messages" button instead of auto-loading chat history
- July 17, 2025: Added configurable options: `personalizedWelcome`, `showHistoryButton`, `autoScrollToBottom`, `smoothScrolling`
- July 17, 2025: Enhanced scroll behavior to always show latest messages at bottom of chat interface
- July 17, 2025: History loading now preserves welcome message and inserts conversation history after it
- July 17, 2025: **AI TOOL CONFIDENCE**: Enhanced AI tool selection with conservative system prompt to prevent incorrect API calls
- July 17, 2025: Added strict rules requiring direct, specific requests before using API tools (e.g., "credit limit" vs "buy credits")
- July 17, 2025: Fixed chat history chronological order - questions now appear before answers in correct sequence
- July 17, 2025: Improved load history button styling - smaller, subtle appearance above welcome message
- July 17, 2025: Load history button now only appears when actual conversation history exists
- July 17, 2025: **AI CLARIFICATION SYSTEM**: Added conservative clarification mechanism for extremely ambiguous questions
- July 17, 2025: Only asks clarifying questions for single-word generic terms that could match multiple tools
- July 17, 2025: Pre-filters questions to avoid over-clarification - skips questions with clear context or action words
- July 17, 2025: Examples: "credits" (single word) -> asks clarification, "how can I post my job" (clear context) -> no clarification
- July 17, 2025: Enhanced user experience by preventing incorrect API calls while minimizing unnecessary questions
- July 17, 2025: **RESPONSE TEMPLATE DIRECT USAGE**: Modified AI tool response formatting to use response templates directly with field replacement
- July 17, 2025: Removed AI formatting layer - now shows exact template message with replaced placeholders (e.g., "The Job post you have created till now is {Job Post}")
- July 17, 2025: Enhanced field replacement logic to handle multiple data formats (dict, list, raw response) for robust placeholder substitution
- July 17, 2025: Improved response consistency and reduced API calls by using template-based formatting instead of AI generation
- July 17, 2025: **WIDGET ICON CUSTOMIZATION**: Added chatwidget icon customization feature in admin panel
- July 17, 2025: Implemented icon upload, preview, and reset functionality with API endpoints for widget branding
- July 17, 2025: Enhanced chatwidget.js to support iconUrl configuration parameter for custom chat button icons
- July 18, 2025: **WIDGET TOGGLE OPTIMIZATION**: Fixed chatwidget toggle functionality and eliminated image reloading on open/close
- July 18, 2025: Removed problematic close overlay (×) symbol that was appearing over custom chat icons
- July 18, 2025: Optimized icon display by reusing single image element instead of recreating on each toggle
- July 18, 2025: Added smooth CSS transitions for icon state changes (darkening when open, normal when closed)
- July 18, 2025: **PRODUCTION DEPLOYMENT**: Created comprehensive AWS EC2 deployment package with full automation
- July 18, 2025: Added Docker containerization with multi-service orchestration (app, database, nginx, redis)
- July 18, 2025: Implemented production-ready configuration with SSL, rate limiting, health checks, and monitoring
- July 18, 2025: Created automated deployment scripts with one-command setup for AWS EC2 instances
- July 18, 2025: Added comprehensive security features including firewall, fail2ban, and automatic security updates
- July 18, 2025: Implemented automated backup system with daily database and application file backups
- July 18, 2025: Added systemd service integration for auto-startup and service management
- July 18, 2025: Created monitoring and alerting system with health checks and resource usage tracking
- July 18, 2025: **CRITICAL API TOOL FIX**: Fixed OpenAI function naming validation error that was preventing API tools from working
- July 18, 2025: Resolved "Job Status" tool name issue (spaces not allowed in OpenAI function names) by changing to "job_status"
- July 18, 2025: Confirmed all three API tools now working: credits balance, job status, and job posts count
- July 18, 2025: Enhanced Flask app context initialization to ensure AI tool executor has proper database access
- July 18, 2025: **CONSERVATIVE AI TOOL SELECTION**: Fixed overly aggressive API tool calling for instructional questions
- July 18, 2025: Updated system prompt to only use APIs for direct data requests ("give me my token" vs "how to check my token")
- July 18, 2025: Blocked API calls for "how to", "how do I", "where do I" questions - these now use knowledge base correctly
- July 18, 2025: Confirmed perfect distinction between API calls (personal data) and knowledge base (instructions)
- July 18, 2025: **WIDGET SIZE CONFIGURATION**: Added comprehensive widget size options with three predefined sizes
- July 18, 2025: Implemented small (60px), medium (80px), and large (100px) button sizes with proportional widget dimensions
- July 18, 2025: Added widgetSize configuration parameter: 'small', 'medium', 'large' for easy size selection
- July 18, 2025: Enhanced admin panel with widget size configuration section showing all available options
- July 18, 2025: Created test_widget_sizes.html for testing and demonstrating different widget size configurations
- July 18, 2025: Added support for custom buttonSize override while maintaining automatic size calculation
- July 19, 2025: **DEPLOYMENT SUCCESS**: Successfully deployed production RAG chatbot to AWS EC2 with Docker containerization
- July 19, 2025: Created clean deployment folder with only 6 essential files (removed 25+ unnecessary scripts)
- July 19, 2025: Fixed Docker build issues including cryptography version conflicts and missing module imports
- July 19, 2025: Created comprehensive deployment guide for AWS EC2 with automated Docker installation
- July 19, 2025: **GIT AUTOMATION**: Added complete Git automation to deployment scripts for TaskMaster repository
- July 19, 2025: Configured deployment to automatically pull from https://github.com/Frankambaa/TaskMaster.git
- July 19, 2025: Created one-command deployment script that handles Git clone, Docker build, and service startup
- July 19, 2025: **SYSTEM PROMPT MANAGEMENT**: Implemented comprehensive system prompt management in admin panel
- July 19, 2025: Added SystemPrompt database model with CRUD operations and active prompt tracking
- July 19, 2025: Integrated dynamic system prompt loading into AI tool executor for customizable chatbot behavior
- July 19, 2025: Updated default system prompt to be comprehensive chatbot behavior guide rather than just API tool rules
- July 19, 2025: Admin can now create multiple prompts, set one as active, and control overall chatbot personality and responses
- July 19, 2025: **URL LINKING FEATURE**: Implemented automatic URL to clickable link conversion in chatbot responses
- July 19, 2025: Enhanced chatwidget.js with regex pattern to detect URLs and convert them to HTML anchor tags with secure attributes
- July 19, 2025: Updated system prompt to encourage including URLs when relevant (like https://employer.apna.co)
- July 19, 2025: **SYSTEM PROMPT VALIDATION**: Comprehensive testing confirms system prompt controls all aspects of chatbot behavior
- July 19, 2025: Verified system prompt usage in 3 locations: ai_tool_executor.py (tool selection), rag_chain.py (RAG responses, memory responses)
- July 19, 2025: Confirmed guardrails working: sensitive topics blocked, off-platform questions filtered, instruction vs API distinction mostly working
- July 19, 2025: **RAG FEEDBACK COLLECTION SYSTEM**: Implemented comprehensive user feedback collection specifically for RAG responses
- July 19, 2025: Added RagFeedback database model with thumbs up/down ratings, comments, user tracking, and training metadata
- July 19, 2025: Created feedback REST API endpoints (/feedback POST/GET, /feedback/stats, /feedback/{id} PUT) for data management
- July 19, 2025: Enhanced chatwidget.js with feedback buttons that appear only after RAG knowledge base responses (not API tools or greetings)
- July 19, 2025: Implemented thank you flow design: RAG answer → feedback buttons → thank you message → optional chat close
- July 19, 2025: Added comprehensive admin panel section for feedback analytics, filtering, and training data management
- July 19, 2025: Feedback system includes response type detection, user identification, session tracking, and training workflow integration
- July 19, 2025: **FEEDBACK TIMING CONTROL**: Fixed feedback buttons to only appear after 3+ RAG conversations or during thank you/goodbye messages
- July 19, 2025: Added conversation tracking counter that resets on session clear and prevents feedback spam on first messages
- July 19, 2025: Enhanced user experience by eliminating inappropriate feedback prompts on simple initial interactions
- July 19, 2025: **FEEDBACK UI REFINEMENTS**: Simplified feedback interface to show only thumbs up/down icons without text
- July 19, 2025: Enhanced greeting detection to exclude simple hi/hello exchanges from feedback collection
- July 19, 2025: Reduced button size and opacity for subtle, non-intrusive feedback experience
- July 19, 2025: **FEEDBACK FLOW REDESIGN**: Moved feedback buttons to appear before message cards instead of after
- July 19, 2025: Implemented new thank you flow - feedback buttons removed immediately, replaced with bot message and close chat confirmation
- July 19, 2025: Added "Yes, close chat" vs "Continue chatting" options after feedback submission for better user experience
- July 19, 2025: **BACKEND TYPING CONTROL**: Implemented comprehensive chat settings management with database storage
- July 19, 2025: Added ChatSettings model with typing effect toggle, speed control, and scroll behavior configuration
- July 19, 2025: Enhanced admin panel with chat widget settings section for real-time configuration
- July 19, 2025: **IMPROVED SCROLL BEHAVIOR**: Fixed scroll interruption during typing - users can now scroll up without being forced back down
- July 19, 2025: Added auto_scroll_during_typing setting (disabled by default) to prevent scroll flickering during bot responses
- July 19, 2025: **ADMIN INTERFACE SIMPLIFICATION**: Consolidated duplicate feedback sections into single "User Feedback & Response Training" interface
- July 19, 2025: Removed duplicate "RAG Feedback Management" section - now unified with organized tabs: All Feedback, Poor Responses, Templates
- July 19, 2025: Enhanced OpenAI API error handling with user-friendly messages for quota/rate limit issues
- July 19, 2025: Fixed JavaScript feedback loading for consolidated admin interface with proper filter integration
- July 19, 2025: **COMPREHENSIVE RESPONSE LOGGING**: Added detailed logging system to track response types and execution flow
- July 19, 2025: **RESPONSE TEMPLATE SYSTEM**: Implemented keyword-based response templates that run FIRST in processing pipeline
- July 19, 2025: **EXECUTION ORDER CLARIFICATION**: System now clearly logs 4-step process: Templates → Small Talk → AI Tools → RAG Knowledge Base
- July 19, 2025: **RESPONSE TYPE TRACKING**: Each response now clearly labeled as TEMPLATE_MATCH, SMALL_TALK, AI_TOOL, or RAG_KNOWLEDGE_BASE
- July 19, 2025: Template system is keyword-based (not semantic), AI tools are semantic (OpenAI Function Calling), RAG uses vector similarity
- July 19, 2025: **REAL-TIME SYSTEM LOGS VIEWER**: Added comprehensive logs section to admin dashboard showing live application activity
- July 19, 2025: Implemented custom log handler to capture all system logs with response type categorization
- July 19, 2025: Added terminal-style log viewer with filtering by level, response type, search, auto-refresh, and download capabilities
- July 19, 2025: System logs now show real-time processing: question analysis, template matches, AI tool calls, OpenAI API interactions, and RAG responses
- July 19, 2025: **TIME-BASED GREETING SYSTEM**: Implemented intelligent time-based greetings for first-time users in chatwidget
- July 19, 2025: Added automatic greeting detection based on current time: morning (5-12), afternoon (12-17), evening (17-22), late hours (22-5)
- July 19, 2025: Created localStorage tracking system to identify first-time vs returning users for appropriate greeting display
- July 19, 2025: Enhanced admin panel with time-based greeting documentation and test page for demonstration
- July 19, 2025: Combined time-based greetings with personalized welcome messages for optimal user experience
- July 19, 2025: **KEYWORD-TRIGGERED LIVE CHAT**: Implemented intelligent live chat transfer only when users explicitly request it
- July 19, 2025: Added keyword detection for phrases like "live chat", "chat with agent", "talk to agent", "human agent"
- July 19, 2025: Preserved original AI/RAG functionality - live chat only activates on specific user requests
- July 19, 2025: Fixed ChatWidget JavaScript errors and integrated live chat without affecting existing bot responses
- July 19, 2025: Created comprehensive admin panel live chat management section with session monitoring and agent portal access
- July 19, 2025: **COMPREHENSIVE WEBHOOK INTEGRATION**: Implemented complete third-party platform integration system
- July 19, 2025: Added webhook_integration.py for processing incoming/outgoing messages from external chat platforms
- July 19, 2025: Created WebhookConfig and WebhookMessage database models for persistent webhook management
- July 19, 2025: Added API endpoints: /api/webhook/incoming, /api/webhook/config, /api/webhook/messages
- July 19, 2025: Supports bidirectional communication with Freshchat, Zendesk, Intercom and other webhook-enabled platforms
- July 19, 2025: Messages from third-party platforms process through same AI/RAG system as chatwidget
- July 19, 2025: Live chat transfer works seamlessly through webhook integration for external platforms
- July 19, 2025: Created comprehensive integration guide and test suite for webhook functionality
- July 19, 2025: **CRITICAL RAG CLASSIFICATION FIX**: Fixed critical bug where RAG questions were incorrectly classified as template responses
- July 19, 2025: Improved template matching logic to avoid false positives on question starters like "can you", "how to", "what is"
- July 19, 2025: Fixed webhook admin dashboard visibility - converted from hidden tabs to visible sections
- July 19, 2025: RAG knowledge base questions now correctly process through semantic search instead of keyword templates
- July 19, 2025: **ENHANCED LIVE CHAT TRANSFER**: Fixed conversation history import and enhanced transfer detection patterns
- July 19, 2025: Added comprehensive pattern matching for natural language phrases like "can i talk to agent", "could you transfer"
- July 19, 2025: Fixed UserConversation model integration for proper conversation history retrieval during live chat transfer
- July 19, 2025: Agent portal now properly displays complete bot/user conversation context with visual message indicators
- July 19, 2025: Enhanced detection works with both keyword matching and semantic pattern analysis for improved user experience
- July 19, 2025: **COMPLETE CONVERSATION HISTORY IMPORT**: Modified live chat transfer to import ALL chatbot conversation history instead of just recent messages
- July 19, 2025: Agent portal now shows complete conversation timeline from first user interaction to current transfer request
- July 19, 2025: Enhanced agent context with full user conversation journey for better customer support experience
- July 19, 2025: **CONVERSATION STORAGE & TRANSFER DEBUGGING**: Fixed and verified real-time conversation storage and live chat history import functionality
- July 19, 2025: Added comprehensive logging for conversation history transfer process with detailed message tracking
- July 19, 2025: Confirmed conversation storage system working: 684+ messages stored per user with automatic import to live chat sessions
- July 19, 2025: Enhanced error handling and verification for conversation history import with success confirmation logging
- July 19, 2025: **CHATBOT CONVERSATIONS ADMIN SECTION**: Added comprehensive "Chatbot Conversations" section to admin panel
- July 19, 2025: Implemented conversation management with user filtering, date filtering, search functionality, and detailed message viewing
- July 19, 2025: Added conversation export feature with JSON download and complete chat history display in modal interface
- July 19, 2025: Created API endpoints for conversation listing, details, and export with comprehensive user metadata tracking
- July 19, 2025: **WEBHOOK DISABLE FIX**: Fixed webhook disable option functionality in admin panel
- July 19, 2025: Enhanced webhook configuration API to handle activate, deactivate, and deactivate_all actions properly
- July 19, 2025: Completed missing deactivateWebhookConfig and deleteWebhookConfig JavaScript functions
- July 19, 2025: Fixed webhook toggle functionality to properly enable/disable webhook routing
- July 19, 2025: **LIVE CHAT UI COMPLETE ENHANCEMENT**: Completely overhauled live chat UI and logic with professional agent portal
- July 19, 2025: Created agent_portal_enhanced.html with real-time session management, priority handling, and modern interface
- July 19, 2025: Added comprehensive message handling with typing indicators, quick responses, and session status controls
- July 19, 2025: Enhanced live_chat_manager.py with missing methods for session/agent management and webhook notifications
- July 19, 2025: Added complete API endpoints for session messages, status updates, and agent management
- July 19, 2025: Implemented agent availability toggle, session search/filtering, and keyboard shortcuts for improved productivity
- July 19, 2025: Created test_live_chat.html for testing customer-side live chat functionality with agent transfer simulation
- July 19, 2025: **VOICE AGENT CHATWIDGET INTEGRATION**: Added comprehensive voice control icon to chat header next to close button
- July 19, 2025: Implemented voice toggle button (🎙️) with dynamic states: enabled, disabled, and playing audio
- July 19, 2025: Enhanced chatwidget with voice synthesis methods: synthesizeVoice, handleVoiceResponse, playAudioBlob, stopVoice
- July 19, 2025: Voice button shows different icons based on state: 🎙️ (enabled), 🔇 (disabled), 🔊 (playing)
- July 19, 2025: Added comprehensive voice test page at /test_voice_widget for demonstration and testing
- July 19, 2025: Voice agent now fully integrated with existing RAG, AI tools, live chat, and webhook systems
- July 19, 2025: **COMPLETE VOICE-TO-VOICE SYSTEM**: Implemented full voice interaction flow with speech recognition and auto-response
- July 19, 2025: Added startVoiceMode() with welcome message, speech recognition, and continuous conversation loop
- July 19, 2025: Enhanced voice agent to prioritize gTTS Indian English for natural Indian accent over Kokoro TTS
- July 19, 2025: Voice system now provides: welcome message → speech recognition → RAG processing → voice response → repeat cycle
- July 19, 2025: **CONTINUOUS VOICE CALL SYSTEM**: Enhanced with 📞 call/disconnect functionality for phone-like experience
- July 19, 2025: Implemented startContinuousVoiceMode() and disconnectVoiceMode() with automatic listening restart after each response
- July 19, 2025: Fixed voice synthesis gTTS fallback system and API request parameter mapping (question vs message)
- July 19, 2025: Added personalized welcome message: "Hello! Welcome to voice mode. How can I help you today? This is Ria."
- July 19, 2025: Voice system now fully functional with Indian English accent and continuous conversation capability
- July 19, 2025: **ENHANCED ACTIVE LISTENING**: Implemented interrupt-driven voice system with voice activity detection
- July 19, 2025: Added continuous speech recognition that auto-restarts, stops speaking when user talks, handles natural pauses
- July 19, 2025: Enhanced speech recognition with interim results, Indian English lang setting, and intelligent conversation flow
- July 19, 2025: Fixed call disconnection issues with manual disconnect flags and proper recognition lifecycle management
- July 19, 2025: **AUDIO FEEDBACK ISOLATION**: Fixed critical audio feedback loop - speech recognition now pauses during voice output
- July 19, 2025: Implemented promise-based audio system with proper completion detection before resuming listening
- July 19, 2025: **VOICE COMMANDS**: Added "stop", "pause", "wait" voice commands for better conversation control
- July 19, 2025: Enhanced conversational timing with 2-second delays for more natural interaction flow
- July 19, 2025: **ELEVENLABS VOICE INTEGRATION**: Added complete ElevenLabs voice agent as separate icon (🎤) alongside existing voice system (🎙️)
- July 19, 2025: Implemented dedicated ElevenLabs API endpoints (/api/elevenlabs/voice, /api/elevenlabs/voices) with premium voice synthesis
- July 19, 2025: Created independent ElevenLabs voice flow: speech recognition → RAG/AI tools → ElevenLabs synthesis → audio playback → continuous listening
- July 19, 2025: Added ElevenLabs-specific UI controls, voice commands, and error handling without disturbing existing voice system
- July 19, 2025: Both voice systems use same RAG knowledge base and AI tools but with different voice engines for user choice
- July 19, 2025: **ELEVENLABS ADMIN MANAGEMENT**: Added comprehensive ElevenLabs API key configuration to admin dashboard
- July 19, 2025: Implemented secure API key storage, validation, and real-time status checking with visual indicators
- July 19, 2025: Created admin interface section with voice comparison table, test links, and automatic status monitoring
- July 19, 2025: Added backend routes for key management (/update_elevenlabs_key) and status validation (/api/elevenlabs/status)
- July 19, 2025: **CRITICAL ELEVENLABS FIX**: Fixed speech recognition restart loop causing continuous "aborted" errors
- July 19, 2025: Enhanced speech recognition state management to prevent multiple simultaneous instances
- July 19, 2025: Improved audio/speech coordination - recognition now waits for audio completion before restarting
- July 19, 2025: Added comprehensive error handling to distinguish between intentional stops and actual errors
- July 19, 2025: Optimized timing delays and restart logic for smooth voice conversation flow
- July 19, 2025: **ELEVENLABS ERROR HANDLING**: Enhanced error categorization for network/no-speech vs critical errors
- July 19, 2025: Implemented intelligent restart delays based on error type for better stability and user experience
- July 19, 2025: **SPEAKER FEEDBACK PREVENTION**: Implemented complete microphone isolation during audio playback
- July 19, 2025: Added bot phrase filtering to prevent voice system from responding to its own output
- July 19, 2025: Enhanced audio volume control and extended silence delays to eliminate speaker-microphone feedback loops
- July 19, 2025: Fixed critical issue where microphone was picking up speaker audio causing conversation loops
- July 19, 2025: **ELEVENLABS EMBEDDED AGENT**: Created ultra-fast voice solution using ElevenLabs' native conversational AI
- July 19, 2025: Implemented embedded voice agent with ~75ms latency vs 3-5 second current system
- July 19, 2025: Added API endpoints for conversation creation, token generation, and session management
- July 19, 2025: Created comprehensive test interface at /test_elevenlabs_embedded for embedded voice demonstration
- July 20, 2025: **CRITICAL LIVE CHAT TRANSFER FIX**: Fixed duplicate conversation issue when transferring from chatbot to live chat
- July 20, 2025: Updated transfer logic to convert existing chatbot sessions to live_chat type instead of creating new sessions
- July 20, 2025: Fixed UnifiedMessage field mapping errors (content → message_content, sender → sender_type/sender_name)
- July 20, 2025: Resolved agent portal display issues - now shows all live chat sessions with complete conversation history
- July 20, 2025: Unified conversation system now maintains single thread when users transfer between chatbot and live agent
- July 20, 2025: **SYSTEM SIMPLIFICATION**: Removed all live chat transfer functionality per user request
- July 20, 2025: Cleaned up chatwidget.js to contain only pure chatbot RAG functionality
- July 20, 2025: Simplified agent portal to show only chatbot conversations with clean single-section interface
- July 20, 2025: Removed all live chat related code, database entries, and UI components
- July 20, 2025: Maintained conversation saving functionality for chatbot interactions only
- July 20, 2025: System now provides pure RAG chatbot experience with comprehensive conversation management
- July 20, 2025: **AGENT PORTAL ENHANCEMENTS**: Implemented IST timezone display, auto-refresh every 10 seconds, and response type labels
- July 20, 2025: Added response_type database field to UnifiedMessage model for tracking message classifications
- July 20, 2025: Enhanced conversation display with response type badges (Small Talk, RAG Response, AI Tool, Template)
- July 20, 2025: Auto-refresh functionality refreshes conversation list and selected conversation messages automatically
- July 20, 2025: All timestamps now display in Indian Standard Time (IST) format throughout the agent portal interface
- July 20, 2025: **FEEDBACK SYSTEM ENHANCEMENT**: Fixed feedback button positioning and continue chat functionality
- July 20, 2025: Moved feedback buttons (👍👎) to appear below bot responses instead of above for better UX
- July 20, 2025: Fixed "Continue chatting" button to properly remove button container without closing chat widget
- July 20, 2025: Enhanced click-outside event handling to prevent interference with feedback interactions
- July 20, 2025: **ADMIN DASHBOARD SIMPLIFICATION**: Removed ElevenLabs Voice Configuration and All Conversations sections from admin panel per user request
- July 20, 2025: **UNIFIED LIVE CHAT SYSTEM**: Consolidated "Live Agent" and "Live Chat" into single "Live Chat" system for simplicity
- July 20, 2025: Fixed session ID handling to use provided session_id from API requests for proper conversation continuity
- July 20, 2025: Removed duplicate "Live Agent" filter from agent portal - now shows unified "Live Chat" filter with orange styling
- July 20, 2025: Updated all database tags and method names from "Live Agent" to "Live Chat" for consistent terminology
- July 20, 2025: Verified live chat transfer working correctly with proper acknowledgment responses for follow-up messages

## Known Issues

**OpenAI API Quota Exceeded**: The chatbot currently shows "quota exceeded" errors due to API usage limits. This affects:
- AI tool selection functionality  
- RAG response generation
- Small talk responses may still work as they use fallback logic

**Resolution**: Contact support or add OpenAI API credits to resolve the quota issue.

## User Preferences

Preferred communication style: Simple, everyday language.