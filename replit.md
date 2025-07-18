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

## User Preferences

Preferred communication style: Simple, everyday language.