# RAG Chatbot with Admin Panel & Session Memory

## Overview
This is a comprehensive RAG (Retrieval-Augmented Generation) chatbot application built with Flask and LangChain. It features document processing, intelligent API routing, session-based memory management, and a modern chat interface with voice input capabilities.

## Core Features

### 🧠 **LangChain Integration & Session Memory**
- **Session-Based Memory**: Each user gets isolated conversation memory with unique session IDs
- **Privacy Protection**: No cross-user data sharing - conversations are completely private
- **Context Awareness**: Chatbot remembers previous interactions within the same session
- **Memory Management**: Clear memory button to reset conversation history
- **LangChain Framework**: Advanced conversation handling with memory components

### 📄 **Document Processing**
- **Multi-Format Support**: PDF and DOCX document upload and processing
- **Smart Chunking**: 500-token chunks with 50-token overlap for optimal retrieval
- **Vector Search**: FAISS-based similarity search for relevant document chunks
- **Bulk Processing**: Upload multiple documents and vectorize them together

### 🔀 **Smart API Routing System**
- **Intelligent Decision Making**: Automatically chooses between API calls and knowledge base queries
- **Keyword Matching**: Configurable keywords trigger specific API rules
- **Curl Integration**: Execute any curl command with dynamic placeholder replacement
- **Priority System**: Rules with higher priority are checked first
- **Database Storage**: Persistent API rule management with SQLite/MySQL/PostgreSQL support

### 🎨 **Modern Chat Interface**
- **ChatGPT-Style UI**: Modern, responsive chat interface with Bootstrap 5
- **Voice Input**: Speech-to-text functionality using Web Speech API
- **Custom Branding**: Upload custom logos for chatbot branding
- **Typing Effects**: Simulated typing indicator for better user experience
- **Markdown Support**: Rich text formatting for bot responses (bold, italic, code)
- **Connection Status**: Visual feedback for API connectivity

### ⚙️ **Admin Management Panel**
- **Document Management**: Upload, view, and delete documents
- **Vectorization Control**: Manual document vectorization with progress feedback
- **API Rules Configuration**: Create, edit, and manage API routing rules
- **System Status**: View uploaded files and system configuration
- **Logo Management**: Upload and manage custom branding

### 🛠️ **Database & Infrastructure**
- **Multi-Database Support**: SQLite (default), MySQL, and PostgreSQL support
- **Auto-Configuration**: Intelligent database selection based on environment
- **Connection Pooling**: Optimized database connections for production
- **Local Development**: SQLite for easy local setup with no external dependencies

## Prerequisites

### 1. Python Installation
- Python 3.8 or higher
- pip (Python package manager)

### 2. OpenAI API Key
You'll need an OpenAI API key to run this application:
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Create a new secret key
5. Copy and save it securely

### 3. Database (Optional)
- **SQLite**: Used by default (no setup required)
- **MySQL**: For production use with better performance
- **PostgreSQL**: For cloud deployment and advanced features

See `DATABASE_SETUP.md` for detailed database configuration instructions.

## Quick Installation

### Windows Users
1. Download the project files
2. Double-click `install_windows.bat` to run the installer
3. Follow the on-screen instructions

### Linux/macOS Users
1. Download the project files
2. Open terminal in the project directory
3. Run: `./install_unix.sh`
4. Follow the on-screen instructions

### Manual Installation

#### Step 1: Download the Project
```bash
# Option 1: If you have git
git clone <your-repository-url>

# Option 2: Download and extract ZIP file
# Download from your repository and extract to a folder
cd rag-chatbot

# Option 2: Download as ZIP and extract
# Then navigate to the extracted folder
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r local_requirements.txt
```

Or install packages manually:
```bash
pip install flask flask-cors flask-sqlalchemy openai faiss-cpu python-docx PyPDF2 python-dotenv tiktoken gunicorn numpy langchain langchain-openai langchain-community pymysql cryptography psycopg2-binary
```

### Step 4: Set Up Environment Variables
Create a `.env` file in the project root directory:
```bash
# Create .env file
touch .env  # On macOS/Linux
# On Windows: create a new file named .env
```

Add your configuration to the `.env` file:
```bash
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Required: Session Secret (use any random string)
SESSION_SECRET=your_random_secret_key_here

# Optional: Database Configuration
# Leave empty to use SQLite (default)
# MYSQL_DATABASE_URL=mysql+pymysql://user:password@localhost:3306/chatbot_db
# DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db

# Optional: Flask Environment
# FLASK_ENV=development
```

### Step 5: Create Required Directories
```bash
mkdir uploads
mkdir faiss_index
mkdir static
mkdir templates
```

### Step 6: Run the Application
```bash
# Using Python directly
python main.py

# Or using Gunicorn (recommended for production)
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

The application will be available at: `http://localhost:5000`

## Project Structure
```
rag-chatbot/
├── app.py                 # Main Flask application
├── main.py               # Application entry point
├── rag_chain.py          # RAG logic and OpenAI integration
├── vectorizer.py         # Document processing and vectorization
├── .env                  # Environment variables (create this)
├── local_requirements.txt # Python dependencies for local installation
├── uploads/              # Uploaded documents storage
├── faiss_index/          # Vector database storage
├── static/
│   ├── app.js           # Frontend JavaScript
│   └── style.css        # Styling
└── templates/
    ├── admin.html       # Admin panel interface
    └── chatbot.html     # Chat interface
```

## Usage Instructions

### 1. Access Admin Panel
- Navigate to `http://localhost:5000/admin`
- Upload PDF or DOCX documents
- Click "Vectorize Documents" to process them
- Manage uploaded files and vector database

### 2. Use the Chatbot
- Navigate to `http://localhost:5000/chatbot`
- Type messages or click the microphone for voice input
- Chat with the AI about your uploaded documents
- Try greetings like "hi" or "hello" for dynamic responses
- Use the "Clear Memory" button to reset conversation history

### 3. Session Memory Features
- **Conversation Context**: The chatbot remembers your previous questions and answers
- **Privacy Protection**: Each user gets their own isolated session
- **Memory Management**: Clear your conversation history anytime
- **Context Awareness**: Ask follow-up questions that reference earlier conversation

### 4. API Rules Management
- Navigate to the "API Rules" section in the admin panel
- Create rules with keywords that trigger external API calls
- Set priority levels for rule matching
- Use `{question}` placeholder in curl commands for dynamic queries
- Toggle rules on/off without deletion

### 5. Custom Branding
- Upload custom logos in the admin panel
- Logos appear in the chat interface
- Supports PNG, JPG, JPEG, GIF, and SVG formats
- Automatically resizes and optimizes images

## Troubleshooting

### Common Issues

#### 1. OpenAI API Error
**Problem**: "The api_key client option must be set"
**Solution**: 
- Check that your `.env` file exists and contains `OPENAI_API_KEY=your_key`
- Ensure there are no extra spaces in your API key
- Restart the application after adding the key

#### 2. Import Errors
**Problem**: "ModuleNotFoundError"
**Solution**:
- Ensure virtual environment is activated
- Install missing packages: `pip install package_name`
- Check Python version compatibility

#### 3. File Upload Issues
**Problem**: Files not uploading or processing
**Solution**:
- Check that `uploads/` directory exists and is writable
- Ensure file size is under 16MB
- Only use PDF or DOCX files

#### 4. Memory Issues
**Problem**: Session memory not working
**Solution**:
- Check that SESSION_SECRET is set in .env file
- Ensure cookies are enabled in your browser
- Clear browser cache and restart application

#### 5. Database Connection Issues
**Problem**: Database connection errors
**Solution**:
- For SQLite: Ensure write permissions in project directory
- For MySQL: Check connection string format and credentials
- For PostgreSQL: Verify database exists and user has permissions
- See `DATABASE_SETUP.md` for detailed configuration

## Advanced Features

### LangChain Integration
- **Conversation Memory**: Uses LangChain's memory components for context tracking
- **Advanced Prompting**: Sophisticated prompt engineering for better responses
- **Session Isolation**: Each user maintains separate conversation context
- **Memory Persistence**: Conversation history maintained throughout session

### Smart API Routing
- **Dynamic Routing**: Automatically switches between knowledge base and API calls
- **Flexible Integration**: Support for any REST API via curl commands
- **Keyword Matching**: Intelligent rule-based routing system
- **Priority System**: Configure rule precedence for complex scenarios

### Multi-Database Support
- **SQLite**: Default choice for local development (no setup required)
- **MySQL**: For production deployments with better performance
- **PostgreSQL**: For cloud deployments and advanced features
- **Auto-Detection**: Automatically selects database based on environment

## Security Considerations

### Session Management
- Each user gets unique session ID for privacy
- No conversation data shared between users
- Session data stored in memory (not persistent across restarts)
- Clear memory functionality for privacy protection

### API Security
- OpenAI API key stored securely in environment variables
- Session secrets for Flask session management
- No API keys exposed in client-side code
- Secure file upload validation

## Production Deployment

### Environment Setup
```bash
# Production environment variables
FLASK_ENV=production
SESSION_SECRET=your_production_secret_key
OPENAI_API_KEY=your_production_api_key
MYSQL_DATABASE_URL=mysql+pymysql://user:password@host:port/database
```

### Gunicorn Configuration
```bash
# Production server command
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app
```

## Support

For issues, questions, or feature requests:
1. Check the `DATABASE_SETUP.md` file for database configuration
2. Review the troubleshooting section above
3. Ensure all environment variables are properly set
4. Check the logs for detailed error messages

## Version History

- **v1.0**: Initial RAG chatbot with document processing
- **v1.1**: Added voice input and dynamic small talk
- **v1.2**: Integrated API routing system with database backend
- **v1.3**: Added MySQL support and comprehensive database configuration
- **v1.4**: LangChain integration with session-based memory management
- **v1.5**: Enhanced privacy features and memory management controls

#### 4. Voice Input Not Working
**Problem**: Microphone button missing or not responding
**Solution**:
- Use a modern browser (Chrome, Firefox, Safari)
- Allow microphone permissions when prompted
- Check browser console for errors

#### 5. Vectorization Fails
**Problem**: "Error during vectorization"
**Solution**:
- Check internet connection for OpenAI API access
- Verify API key is valid and has credits
- Ensure documents contain readable text

## Development Tips

### Running in Development Mode
```bash
# Set Flask environment for development
export FLASK_ENV=development  # On macOS/Linux
set FLASK_ENV=development     # On Windows

python main.py
```

### Adding New Dependencies
```bash
# Install new package
pip install package_name

# Update requirements.txt
pip freeze > requirements.txt
```

### Logs and Debugging
- Check console output for error messages
- Enable debug mode in Flask for detailed error pages
- Use browser developer tools to check network requests

## Security Considerations

1. **API Key Protection**: Never commit your `.env` file to version control
2. **File Uploads**: The application limits file size to 16MB for security
3. **Local Network**: By default, the app binds to `0.0.0.0` - restrict this in production
4. **Dependencies**: Keep packages updated for security patches

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Ensure your OpenAI API key is valid and has credits
4. Check that all required files are present

## License
This project is provided as-is for educational and development purposes.