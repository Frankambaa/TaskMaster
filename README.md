# RAG Chatbot with Admin Panel - Local Installation Guide

## Overview
This is a complete RAG (Retrieval-Augmented Generation) chatbot application with document upload, vectorization, and voice input capabilities.

## Features
- 📄 PDF and DOCX document upload and processing
- 🔍 Vector-based document search using FAISS
- 🤖 AI-powered responses using OpenAI GPT-4o
- 🎤 Voice input with speech-to-text conversion
- 💬 Dynamic small talk responses
- 🎨 ChatGPT-style user interface
- ⚙️ Admin panel for document management

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

## Installation Steps

### Step 1: Download the Project
```bash
# Option 1: If you have git
git clone <your-repository-url>
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
pip install flask flask-cors openai faiss-cpu python-docx PyPDF2 python-dotenv tiktoken gunicorn numpy
```

### Step 4: Set Up Environment Variables
Create a `.env` file in the project root directory:
```bash
# Create .env file
touch .env  # On macOS/Linux
# On Windows: create a new file named .env
```

Add your OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
SESSION_SECRET=your_secret_key_for_flask_sessions
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