import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from vectorizer import DocumentVectorizer
from rag_chain import RAGChain
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable CORS for all routes
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
FAISS_INDEX_FOLDER = 'faiss_index'
LOGO_FOLDER = 'static/logos'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FAISS_INDEX_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize components
vectorizer = DocumentVectorizer()
rag_chain = RAGChain()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('chatbot'))

@app.route('/admin')
def admin():
    """Admin panel for file upload and vectorization"""
    # Get list of uploaded files
    uploaded_files = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if allowed_file(filename):
                uploaded_files.append(filename)
    
    # Check if vector index exists
    index_exists = os.path.exists(os.path.join(FAISS_INDEX_FOLDER, 'index.faiss'))
    
    # Get current logo
    current_logo = None
    if os.path.exists(LOGO_FOLDER):
        for filename in os.listdir(LOGO_FOLDER):
            if allowed_image_file(filename):
                current_logo = filename
                break
    
    return render_template('admin.html', 
                         uploaded_files=uploaded_files, 
                         index_exists=index_exists,
                         current_logo=current_logo)

@app.route('/chatbot')
def chatbot():
    """Chatbot interface for end users"""
    # Get current logo
    current_logo = None
    if os.path.exists(LOGO_FOLDER):
        for filename in os.listdir(LOGO_FOLDER):
            if allowed_image_file(filename):
                current_logo = f'/static/logos/{filename}'
                break
    
    return render_template('chatbot.html', current_logo=current_logo)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('admin'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        flash(f'File {filename} uploaded successfully!')
        logging.info(f"File uploaded: {filename}")
    else:
        flash('Invalid file type. Please upload PDF or DOCX files only.')
    
    return redirect(url_for('admin'))

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    """Handle logo upload"""
    if 'logo' not in request.files:
        flash('No logo file selected')
        return redirect(url_for('admin'))
    
    file = request.files['logo']
    if file.filename == '':
        flash('No logo file selected')
        return redirect(url_for('admin'))
    
    if file and allowed_image_file(file.filename):
        # Remove existing logo files
        if os.path.exists(LOGO_FOLDER):
            for filename in os.listdir(LOGO_FOLDER):
                if allowed_image_file(filename):
                    os.remove(os.path.join(LOGO_FOLDER, filename))
        
        # Save new logo
        filename = secure_filename(file.filename)
        # Keep original extension but use consistent name
        ext = filename.rsplit('.', 1)[1].lower()
        logo_filename = f'logo.{ext}'
        filepath = os.path.join(LOGO_FOLDER, logo_filename)
        file.save(filepath)
        flash(f'Logo uploaded successfully!')
        logging.info(f"Logo uploaded: {logo_filename}")
    else:
        flash('Invalid file type. Please upload PNG, JPG, JPEG, GIF, or SVG files only.')
    
    return redirect(url_for('admin'))

@app.route('/vectorize', methods=['POST'])
def vectorize():
    """Vectorize uploaded documents"""
    try:
        # Get all uploaded files
        uploaded_files = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                if allowed_file(filename):
                    uploaded_files.append(os.path.join(UPLOAD_FOLDER, filename))
        
        if not uploaded_files:
            flash('No files to vectorize. Please upload documents first.')
            return redirect(url_for('admin'))
        
        # Process documents and create vector index
        vectorizer.process_documents(uploaded_files, FAISS_INDEX_FOLDER)
        flash('Documents vectorized successfully!')
        logging.info("Documents vectorized successfully")
        
    except Exception as e:
        flash(f'Error during vectorization: {str(e)}')
        logging.error(f"Vectorization error: {str(e)}")
    
    return redirect(url_for('admin'))

@app.route('/ask', methods=['POST'])
def ask():
    """Chat endpoint for answering questions"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Get answer from RAG chain
        answer = rag_chain.get_answer(question, FAISS_INDEX_FOLDER)
        
        # Get current logo
        current_logo = None
        if os.path.exists(LOGO_FOLDER):
            for filename in os.listdir(LOGO_FOLDER):
                if allowed_image_file(filename):
                    current_logo = f'/static/logos/{filename}'
                    break
        
        return jsonify({
            'answer': answer,
            'status': 'success',
            'logo': current_logo
        })
        
    except Exception as e:
        logging.error(f"Error in ask endpoint: {str(e)}")
        return jsonify({
            'error': 'Sorry, I encountered an error while processing your question. Please try again.',
            'status': 'error'
        }), 500

@app.route('/clear_index', methods=['POST'])
def clear_index():
    """Clear the vector index"""
    try:
        # Remove FAISS index files
        index_file = os.path.join(FAISS_INDEX_FOLDER, 'index.faiss')
        metadata_file = os.path.join(FAISS_INDEX_FOLDER, 'metadata.json')
        
        if os.path.exists(index_file):
            os.remove(index_file)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        flash('Vector index cleared successfully!')
        logging.info("Vector index cleared")
        
    except Exception as e:
        flash(f'Error clearing index: {str(e)}')
        logging.error(f"Error clearing index: {str(e)}")
    
    return redirect(url_for('admin'))

@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    """Delete an uploaded file"""
    try:
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(f'File {filename} deleted successfully!')
            logging.info(f"File deleted: {filename}")
        else:
            flash(f'File {filename} not found.')
            
    except Exception as e:
        flash(f'Error deleting file: {str(e)}')
        logging.error(f"Error deleting file: {str(e)}")
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
