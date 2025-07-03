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
- **Purpose**: Implements the retrieval-augmented generation logic
- **Chat Model**: Uses GPT-4o for response generation
- **Small Talk Handling**: Built-in responses for common greetings and pleasantries
- **Retrieval**: Top-k similarity search (k=3) for relevant document chunks

### 3. Flask Application (`app.py`)
- **Routes**: 
  - `/` - Redirects to chatbot interface
  - `/admin` - File upload and vectorization management
  - `/chatbot` - Main chat interface
  - `/ask` - API endpoint for chat queries
- **File Handling**: Secure file upload with size limits (16MB)
- **Session Management**: Flash messages for user feedback

### 4. Frontend Chat Interface
- **Real-time Chat**: AJAX-based messaging system
- **Typing Effects**: Simulated typing indicator for better UX
- **Connection Status**: Visual feedback for API connectivity
- **Responsive Design**: Works on desktop and mobile devices

## Data Flow

1. **Document Upload**: Admin uploads PDF/DOCX files through the admin panel
2. **Text Extraction**: System extracts text from uploaded documents
3. **Chunking**: Text is split into overlapping chunks for better retrieval
4. **Vectorization**: Each chunk is converted to embeddings using OpenAI API
5. **Index Storage**: FAISS index is saved to disk for persistence
6. **Query Processing**: User questions are embedded and matched against stored vectors
7. **Response Generation**: Relevant chunks are used as context for GPT-4o to generate answers

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

### Environment Configuration
- **OpenAI API Key**: Required environment variable `OPENAI_API_KEY`
- **Session Secret**: `SESSION_SECRET` for Flask session management
- **File Storage**: Local filesystem for uploads and FAISS indices

### Directory Structure
```
uploads/          # Uploaded documents
faiss_index/      # FAISS vector indices
static/           # CSS and JavaScript files
templates/        # HTML templates
```

### Production Considerations
- File upload size limited to 16MB
- CORS enabled for cross-origin requests
- ProxyFix middleware for proper header handling
- Debug mode configurable for development/production

## Changelog
- July 03, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.