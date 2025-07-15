import os
import logging
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from vectorizer import DocumentVectorizer
from rag_chain import RAGChain
from models import db, ApiRule
from api_executor import ApiExecutor
from session_memory import session_manager
import json
import subprocess
import shlex

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration - prioritize local development
mysql_url = os.environ.get('MYSQL_DATABASE_URL')
database_url = os.environ.get('DATABASE_URL')

# For now, use SQLite by default to avoid connection issues
if mysql_url:
    # MySQL configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = mysql_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 20,
        'pool_size': 10,
        'max_overflow': 20
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    print("Using MySQL database")
else:
    # SQLite for local development (default)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    print("Using SQLite database for local development")

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

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
api_executor = ApiExecutor()

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
    
    # Get API rules
    api_rules = ApiRule.query.order_by(ApiRule.priority.desc(), ApiRule.created_at.desc()).all()
    
    return render_template('admin.html', 
                         uploaded_files=uploaded_files, 
                         index_exists=index_exists,
                         current_logo=current_logo,
                         api_rules=api_rules)

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
    """Chat endpoint for answering questions with session-based memory"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Get or create session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        logging.info(f"Processing question for session: {session_id}")
        
        # First check if we have any API rules that match this question
        api_rules = ApiRule.query.filter_by(active=True).all()
        matching_rule = api_executor.find_matching_rule(question, api_rules)
        
        if matching_rule:
            # Execute API call
            logging.info(f"Using API rule: {matching_rule.name}")
            api_result = api_executor.execute_curl_command(matching_rule.curl_command, question)
            answer = api_executor.format_api_response(api_result, matching_rule.name)
            response_type = 'api'
            
            # Add to session memory for API responses too
            session_manager.add_user_message(session_id, question)
            session_manager.add_ai_message(session_id, answer)
        else:
            # Fall back to RAG chain with session memory
            logging.info(f"No API rule matched, using RAG chain with session memory")
            answer = rag_chain.get_answer(question, FAISS_INDEX_FOLDER, session_id)
            response_type = 'rag'
        
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
            'logo': current_logo,
            'response_type': response_type
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

# API Rules management routes
@app.route('/api_rules', methods=['POST'])
def add_api_rule():
    """Add a new API rule"""
    try:
        data = request.get_json()
        
        rule = ApiRule(
            name=data['name'],
            keywords=data['keywords'],
            curl_command=data['curl_command'],
            priority=int(data.get('priority', 0)),
            active=data.get('active', True)
        )
        
        db.session.add(rule)
        db.session.commit()
        
        flash(f'API rule "{rule.name}" added successfully!')
        return jsonify({'success': True, 'message': 'API rule added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding API rule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api_rules/<int:rule_id>', methods=['PUT'])
def update_api_rule(rule_id):
    """Update an API rule"""
    try:
        rule = ApiRule.query.get_or_404(rule_id)
        data = request.get_json()
        
        rule.name = data['name']
        rule.keywords = data['keywords']
        rule.curl_command = data['curl_command']
        rule.priority = int(data.get('priority', 0))
        rule.active = data.get('active', True)
        
        db.session.commit()
        
        flash(f'API rule "{rule.name}" updated successfully!')
        return jsonify({'success': True, 'message': 'API rule updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating API rule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api_rules/<int:rule_id>', methods=['DELETE'])
def delete_api_rule(rule_id):
    """Delete an API rule"""
    try:
        rule = ApiRule.query.get_or_404(rule_id)
        rule_name = rule.name
        
        db.session.delete(rule)
        db.session.commit()
        
        flash(f'API rule "{rule_name}" deleted successfully!')
        return jsonify({'success': True, 'message': 'API rule deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting API rule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api_rules/<int:rule_id>/toggle', methods=['POST'])
def toggle_api_rule(rule_id):
    """Toggle active status of an API rule"""
    try:
        rule = ApiRule.query.get_or_404(rule_id)
        rule.active = not rule.active
        
        db.session.commit()
        
        status = "activated" if rule.active else "deactivated"
        flash(f'API rule "{rule.name}" {status}!')
        return jsonify({'success': True, 'active': rule.active})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling API rule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_session', methods=['POST'])
def clear_session():
    """Clear current session memory"""
    try:
        if 'session_id' in session:
            session_id = session['session_id']
            session_manager.clear_session(session_id)
            session.pop('session_id', None)
            logging.info(f"Session memory cleared for session: {session_id}")
            return jsonify({'success': True, 'message': 'Session memory cleared'})
        else:
            return jsonify({'success': True, 'message': 'No active session to clear'})
    
    except Exception as e:
        logging.error(f"Error clearing session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/session_info', methods=['GET'])
def session_info():
    """Get information about current session"""
    try:
        if 'session_id' in session:
            session_id = session['session_id']
            stats = session_manager.get_session_stats(session_id)
            return jsonify({
                'session_id': session_id,
                'stats': stats
            })
        else:
            return jsonify({
                'session_id': None,
                'stats': {'exists': False}
            })
    
    except Exception as e:
        logging.error(f"Error getting session info: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
