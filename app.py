import os
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from vectorizer import DocumentVectorizer
from rag_chain import RAGChain
from models import db, UnifiedConversation, UnifiedMessage, ApiRule, ApiTool, UserConversation, SystemPrompt, RagFeedback, ChatSettings, ResponseTemplate, LiveChatSession, LiveChatMessage, LiveChatAgent, WebhookConfig, WebhookMessage
from session_memory import session_manager
from voice_agent import voice_agent
from elevenlabs_embedded import embedded_agent
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
WIDGET_ICON_FOLDER = 'static/widget_icons'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FAISS_INDEX_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)
os.makedirs(WIDGET_ICON_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize components
vectorizer = DocumentVectorizer()
# Initialize RAG chain after database is ready
with app.app_context():
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
    
    # Get AI tools
    ai_tools = ApiTool.query.order_by(ApiTool.priority.desc(), ApiTool.created_at.desc()).all()
    
    return render_template('admin.html', 
                         uploaded_files=uploaded_files, 
                         index_exists=index_exists,
                         current_logo=current_logo,
                         ai_tools=ai_tools)

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

@app.route('/test_widget_history.html')
def test_widget_history():
    """Test page for widget history functionality"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_widget_history.html')

@app.route('/test_widget_sizes.html')
def test_widget_sizes():
    """Test page for widget size functionality"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_widget_sizes.html')

@app.route('/test_voice')
def test_voice():
    """Voice agent test page"""
    return render_template('test_voice_agent.html')

@app.route('/test_voice_widget')
def test_voice_widget():
    """Voice-enabled chatwidget test page"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_voice_chatwidget.html')

@app.route('/test_voice_icon')
def test_voice_icon():
    """Simple voice icon test page"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_voice_icon.html')

@app.route('/test_time_based_greeting.html')
def test_time_based_greeting():
    """Test page for time-based greeting functionality"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_time_based_greeting.html')

@app.route('/test_feedback_buttons.html')
def test_feedback_buttons():
    """Test page for feedback buttons functionality"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_feedback_buttons.html')

@app.route('/test_live_agent_detection.html')
def test_live_agent_detection():
    """Test page for live agent detection functionality"""
    from flask import send_from_directory
    return send_from_directory('.', 'test_live_agent_detection.html')

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
    """Enhanced chat endpoint for answering questions with user-specific persistent memory"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Extract user parameters if provided
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        device_id = data.get('device_id')
        
        # Determine user identifier (priority: user_id > email > device_id)
        user_identifier = user_id or email or device_id
        
        # Use provided session_id or create/get from session
        session_id = data.get('session_id')
        if not session_id:
            if 'session_id' not in session:
                session['session_id'] = str(uuid.uuid4())
            session_id = session['session_id']
        
        # Log the request with user context
        if user_identifier:
            logging.info(f"Processing question for user: {user_identifier} (username: {username})")
        else:
            logging.info(f"Processing question for session: {session_id}")
            
        # Check if conversation is already in native live chat mode
        unified_conv = UnifiedConversation.get_or_create(
            session_id=session_id,
            user_identifier=user_identifier,
            username=username,
            email=email,
            device_id=device_id
        )
        
        if unified_conv.is_live_chat_active():
            # Conversation is in live chat mode - don't use RAG, just acknowledge messages
            unified_conv.add_message('user', question, user_identifier, username, 'text', 'live_chat_message')
            
            answer = "Your message has been noted. An agent will review and respond to your message shortly. Thank you for your patience."
            response_type = 'live_chat_active'
            
            # Store bot response
            unified_conv.add_message('assistant', answer, 'system', 'Assistant', 'text', response_type)
            
            # Get current logo for consistent response format
            current_logo = None
            if os.path.exists(LOGO_FOLDER):
                for filename in os.listdir(LOGO_FOLDER):
                    if allowed_image_file(filename):
                        current_logo = f'/static/logos/{filename}'
                        break
            
            return jsonify({
                'answer': answer,
                'logo': current_logo,
                'response_type': response_type,
                'session_info': {
                    'session_id': session_id,
                    'user_identifier': user_identifier,
                    'mode': 'live_chat'
                }
            })
        
        # Live chat transfer detection with semantic phrase patterns
        live_chat_keywords = [
            'live chat', 'chat with agent', 'talk to agent', 'talk with agent', 'human agent', 'speak to human', 
            'connect to agent', 'i want to talk', 'speak with someone', 'customer service', 'support agent', 
            'real person', 'human help', 'agent help', 'call center', 'representative', 'operator', 
            'staff member', 'transfer me', 'escalate', 'human support', 'live support', 'personal assistance',
            'can i talk to', 'could you transfer', 'transfer to agent', 'connect me to', 'talk to someone',
            'speak to agent', 'contact agent', 'reach agent', 'get agent', 'agent please'
        ]
        
        # Semantic pattern matching for natural language requests
        question_lower = question.lower()
        live_chat_patterns = [
            'talk to' in question_lower and 'agent' in question_lower,
            'talk with' in question_lower and 'agent' in question_lower,
            'transfer' in question_lower and ('agent' in question_lower or 'live' in question_lower),
            'connect' in question_lower and ('agent' in question_lower or 'human' in question_lower),
            'speak' in question_lower and ('agent' in question_lower or 'someone' in question_lower),
            'chat with' in question_lower and ('agent' in question_lower or 'human' in question_lower),
            'can i' in question_lower and 'talk' in question_lower and ('agent' in question_lower or 'someone' in question_lower),
            'could you' in question_lower and ('transfer' in question_lower or 'connect' in question_lower),
            'need help' in question_lower and 'agent' in question_lower,
            'speak to' in question_lower and ('human' in question_lower or 'person' in question_lower)
        ]
        
        is_live_chat_request = any(keyword in question.lower() for keyword in live_chat_keywords) or any(live_chat_patterns)
        
        if is_live_chat_request:
            # LIVE CHAT TRANSFER - Shows "Transferring to agent" and disables RAG
            try:
                # Create or get unified conversation
                unified_conv = UnifiedConversation.get_or_create(
                    session_id=session_id,
                    user_identifier=user_identifier,
                    username=username,
                    email=email,
                    device_id=device_id
                )
                
                # Set live chat mode (disables RAG)
                unified_conv.set_live_chat_mode()
                
                # Store the user's request message
                unified_conv.add_message('user', question, user_identifier, username, 'text', 'live_chat_request')
                
                answer = "🔄 **Transferring to agent...** \n\nI'm connecting you with our customer support team. Your conversation history has been preserved and an agent will be with you shortly to assist with your request."
                response_type = 'live_chat_transfer'
                
                # Store bot response
                unified_conv.add_message('assistant', answer, 'system', 'Assistant', 'text', response_type)
                
                logging.info(f"✅ LIVE CHAT: Activated for session {session_id} - RAG disabled")
                
                # Get current logo for consistent response format
                current_logo = None
                if os.path.exists(LOGO_FOLDER):
                    for filename in os.listdir(LOGO_FOLDER):
                        if allowed_image_file(filename):
                            current_logo = f'/static/logos/{filename}'
                            break
                
                return jsonify({
                    'answer': answer,
                    'logo': current_logo,
                    'response_type': response_type,
                    'session_info': {
                        'session_id': session_id,
                        'user_identifier': user_identifier,
                        'mode': 'live_chat'
                    }
                })
                
            except Exception as e:
                logging.error(f"Error activating live chat: {e}")
                answer = "I'll connect you with our customer support team. Please wait while I transfer your chat."
                response_type = 'live_chat_transfer'
                
                # Get current logo for consistent response format
                current_logo = None
                if os.path.exists(LOGO_FOLDER):
                    for filename in os.listdir(LOGO_FOLDER):
                        if allowed_image_file(filename):
                            current_logo = f'/static/logos/{filename}'
                            break
                
                return jsonify({
                    'answer': answer,
                    'logo': current_logo,
                    'response_type': response_type,
                    'session_info': {
                        'session_id': session_id,
                        'user_identifier': user_identifier,
                        'mode': 'live_chat'
                    }
                })
                response_type = 'native_live_chat_transfer'
            
        else:
            # Normal AI/RAG processing
            logging.info(f"Using RAG chain with AI tool selection and {'user-based' if user_identifier else 'session-based'} memory")
            answer = rag_chain.get_answer(question, FAISS_INDEX_FOLDER, session_id, user_identifier, username, email, device_id)
            response_type = 'rag_with_ai_tools'
        
        # Get current logo
        current_logo = None
        if os.path.exists(LOGO_FOLDER):
            for filename in os.listdir(LOGO_FOLDER):
                if allowed_image_file(filename):
                    current_logo = f'/static/logos/{filename}'
                    break
        
        # Include user information in response if available
        user_info = {}
        if user_identifier:
            user_info = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'device_id': device_id,
                'session_type': 'persistent'
            }
        else:
            user_info = {
                'session_id': session_id,
                'session_type': 'temporary'
            }
        
        return jsonify({
            'answer': answer,
            'status': 'success',
            'logo': current_logo,
            'response_type': response_type,
            'user_info': user_info
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


# AI Tool Management Routes
@app.route('/ai_tools', methods=['GET'])
def get_ai_tools():
    """Get all AI tools"""
    try:
        tools = ApiTool.query.all()
        return jsonify({'tools': [tool.to_dict() for tool in tools]})
    except Exception as e:
        logging.error(f"Error fetching AI tools: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ai_tools', methods=['POST'])
def add_ai_tool():
    """Add a new AI tool"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'parameters', 'curl_command']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate parameters as JSON
        try:
            json.loads(data['parameters'])
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': 'Parameters must be valid JSON'}), 400
        
        # Validate response_mapping as JSON if provided
        if data.get('response_mapping'):
            try:
                json.loads(data['response_mapping'])
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': 'Response mapping must be valid JSON'}), 400
        
        new_tool = ApiTool(
            name=data['name'],
            description=data['description'],
            parameters=data['parameters'],
            curl_command=data['curl_command'],
            response_mapping=data.get('response_mapping', '{}'),
            response_template=data.get('response_template', ''),
            priority=int(data.get('priority', 0)),
            active=data.get('active', True)
        )
        
        db.session.add(new_tool)
        db.session.commit()
        
        flash(f'AI tool "{new_tool.name}" added successfully!')
        return jsonify({'success': True, 'message': 'AI tool added successfully', 'tool': new_tool.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding AI tool: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ai_tools/<int:tool_id>', methods=['PUT'])
def update_ai_tool(tool_id):
    """Update an AI tool"""
    try:
        tool = ApiTool.query.get_or_404(tool_id)
        data = request.get_json()
        
        # Validate parameters as JSON
        if 'parameters' in data:
            try:
                json.loads(data['parameters'])
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': 'Parameters must be valid JSON'}), 400
        
        # Validate response_mapping as JSON if provided
        if data.get('response_mapping'):
            try:
                json.loads(data['response_mapping'])
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': 'Response mapping must be valid JSON'}), 400
        
        tool.name = data.get('name', tool.name)
        tool.description = data.get('description', tool.description)
        tool.parameters = data.get('parameters', tool.parameters)
        tool.curl_command = data.get('curl_command', tool.curl_command)
        tool.response_mapping = data.get('response_mapping', tool.response_mapping)
        tool.response_template = data.get('response_template', tool.response_template)
        tool.priority = int(data.get('priority', tool.priority))
        tool.active = data.get('active', tool.active)
        
        db.session.commit()
        
        flash(f'AI tool "{tool.name}" updated successfully!')
        return jsonify({'success': True, 'message': 'AI tool updated successfully', 'tool': tool.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating AI tool: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ai_tools/<int:tool_id>', methods=['DELETE'])
def delete_ai_tool(tool_id):
    """Delete an AI tool"""
    try:
        tool = ApiTool.query.get_or_404(tool_id)
        tool_name = tool.name
        
        db.session.delete(tool)
        db.session.commit()
        
        flash(f'AI tool "{tool_name}" deleted successfully!')
        return jsonify({'success': True, 'message': 'AI tool deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting AI tool: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ai_tools/<int:tool_id>/toggle', methods=['POST'])
def toggle_ai_tool(tool_id):
    """Toggle active status of an AI tool"""
    try:
        tool = ApiTool.query.get_or_404(tool_id)
        tool.active = not tool.active
        
        db.session.commit()
        
        status = "activated" if tool.active else "deactivated"
        flash(f'AI tool "{tool.name}" {status}!')
        return jsonify({'success': True, 'active': tool.active})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling AI tool: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test_api_response', methods=['POST'])
def test_api_response():
    """Test API response for field mapping configuration"""
    try:
        data = request.get_json()
        curl_command = data.get('curl_command', '')
        
        if not curl_command:
            return jsonify({'success': False, 'error': 'No curl command provided'}), 400
        
        # Execute the curl command using subprocess
        import subprocess
        import json
        
        # Process the curl command (replace any placeholders with test values)
        processed_command = curl_command
        
        # Replace common placeholders with test values
        processed_command = processed_command.replace('{question}', 'test')
        processed_command = processed_command.replace('{user_query}', 'test')
        processed_command = processed_command.replace('{query}', 'test')
        
        # Execute the command
        result = subprocess.run(
            processed_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                # Try to parse as JSON
                response_data = json.loads(result.stdout)
                return jsonify({
                    'success': True,
                    'data': response_data,
                    'raw_output': result.stdout
                })
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                return jsonify({
                    'success': True,
                    'data': {'response': result.stdout},
                    'raw_output': result.stdout
                })
        else:
            return jsonify({
                'success': False,
                'error': f'Command failed with return code {result.returncode}',
                'stderr': result.stderr,
                'stdout': result.stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'API request timed out'}), 500
    except Exception as e:
        logging.error(f"Error testing API response: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_session', methods=['POST'])
def clear_session():
    """Clear current session memory (user-based or session-based)"""
    try:
        data = request.get_json() or {}
        
        # Extract user parameters if provided
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        device_id = data.get('device_id')
        
        # Determine user identifier (priority: user_id > email > device_id)
        user_identifier = user_id or email or device_id
        
        if user_identifier:
            # Clear user-based conversation
            session_manager.clear_session(None, user_identifier)
            logging.info(f"User conversation cleared for user: {user_identifier}")
            return jsonify({
                'success': True, 
                'message': 'User conversation cleared',
                'session_type': 'persistent',
                'user_identifier': user_identifier
            })
        elif 'session_id' in session:
            # Clear session-based conversation
            session_id = session['session_id']
            session_manager.clear_session(session_id)
            session.pop('session_id', None)
            logging.info(f"Session memory cleared for session: {session_id}")
            return jsonify({
                'success': True, 
                'message': 'Session memory cleared',
                'session_type': 'temporary',
                'session_id': session_id
            })
        else:
            return jsonify({'success': True, 'message': 'No active session or user to clear'})
    
    except Exception as e:
        logging.error(f"Error clearing session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/session_info', methods=['GET', 'POST'])
def session_info():
    """Get information about current session (user-based or session-based)"""
    try:
        data = request.get_json() if request.method == 'POST' else {}
        
        # Extract user parameters if provided
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        device_id = data.get('device_id')
        
        # Determine user identifier (priority: user_id > email > device_id)
        user_identifier = user_id or email or device_id
        
        if user_identifier:
            # Get user-based conversation info
            stats = session_manager.get_session_stats(None, user_identifier)
            user_info = session_manager.get_user_conversation_info(user_identifier)
            
            return jsonify({
                'session_type': 'persistent',
                'user_identifier': user_identifier,
                'username': username,
                'email': email,
                'device_id': device_id,
                'stats': stats,
                'user_info': user_info
            })
        elif 'session_id' in session:
            # Get session-based conversation info
            session_id = session['session_id']
            stats = session_manager.get_session_stats(session_id)
            
            return jsonify({
                'session_type': 'temporary',
                'session_id': session_id,
                'stats': stats
            })
        else:
            return jsonify({
                'session_type': 'none',
                'session_id': None,
                'stats': {'exists': False}
            })
    
    except Exception as e:
        logging.error(f"Error getting session info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/widget_history', methods=['POST'])
def widget_history():
    """Get chat history for widget (last N messages)"""
    try:
        data = request.get_json()
        
        # Extract user parameters
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        device_id = data.get('device_id')
        limit = data.get('limit', 10)  # Default to 10 messages
        
        # Determine user identifier (priority: user_id > email > device_id)
        user_identifier = user_id or email or device_id
        
        if not user_identifier:
            return jsonify({'history': []})
        
        # Get user conversation from database
        user_conv = UserConversation.query.filter_by(user_identifier=user_identifier).first()
        
        if not user_conv:
            return jsonify({'history': []})
        
        # Get conversation history
        conversation_history = user_conv.get_conversation_history()
        
        # Get last N messages
        if limit and len(conversation_history) > limit:
            conversation_history = conversation_history[-limit:]
        
        # Format messages for widget display
        formatted_history = []
        for message in conversation_history:
            # Handle different message formats that might be stored
            if isinstance(message, dict):
                # New format: direct message dict
                role = message.get('role', message.get('type', 'user'))
                content = message.get('content', '')
                timestamp = message.get('timestamp', '')
            else:
                # Handle any other format
                role = 'user'
                content = str(message)
                timestamp = ''
            
            # Convert role format if needed
            if role == 'human':
                role = 'user'
            elif role == 'ai':
                role = 'assistant'
            
            formatted_history.append({
                'role': role,
                'content': content,
                'timestamp': timestamp
            })
        
        return jsonify({
            'history': formatted_history,
            'user_identifier': user_identifier,
            'total_messages': len(conversation_history)
        })
    
    except Exception as e:
        logging.error(f"Error getting widget history: {str(e)}")
        return jsonify({'error': str(e), 'history': []}), 500

@app.route('/user_conversations', methods=['GET'])
def user_conversations():
    """Get list of all user conversations (admin endpoint)"""
    try:
        conversations = UserConversation.query.order_by(UserConversation.last_activity.desc()).all()
        return jsonify({
            'status': 'success',
            'conversations': [conv.to_dict() for conv in conversations]
        })
    except Exception as e:
        logging.error(f"Error getting user conversations: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error getting user conversations'}), 500

@app.route('/user_conversation/<user_identifier>', methods=['GET'])
def get_user_conversation(user_identifier):
    """Get specific user conversation details"""
    try:
        conversation = UserConversation.query.filter_by(user_identifier=user_identifier).first()
        if not conversation:
            return jsonify({'status': 'error', 'message': 'User conversation not found'}), 404
            
        return jsonify({
            'status': 'success',
            'conversation': conversation.to_dict(),
            'history': conversation.get_conversation_history()
        })
    except Exception as e:
        logging.error(f"Error getting user conversation: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error getting user conversation'}), 500

@app.route('/widget_demo')
def widget_demo():
    """Serve the widget demo page"""
    try:
        with open('widget_example.html', 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Widget demo page not found", 404

@app.route('/test_widget')
def test_widget():
    """Simple test page for widget integration"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Widget Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .info { background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chatbot Widget Test</h1>
            <div class="info">
                <p>This is a simple test page demonstrating the chatbot widget integration.</p>
                <p>The widget should appear as a chat icon in the bottom-right corner.</p>
                <p>Click the icon to start chatting!</p>
            </div>
        </div>
        
        <!-- Load the chatbot widget -->
        <script src="/static/chatwidget.js"></script>
        <script>
            ChatWidget.init({
                apiUrl: window.location.origin,
                user_id: 'test_user_123',
                username: 'Test User',
                email: 'test@example.com',
                device_id: 'web_browser_test',
                position: 'bottom-right',
                title: 'AI Assistant',
                welcomeMessage: 'Hello! I\\'m your AI assistant. How can I help you today?'
            });
        </script>
    </body>
    </html>
    '''

@app.route('/test_upload')
def test_upload():
    """Test page for upload functionality"""
    with open('test_upload.html', 'r') as f:
        return f.read()

@app.route('/test_widget_fix')
def test_widget_fix():
    """Test page for fixed widget integration"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Widget Test - Fixed</title>
        <!-- Add to <head> section -->
        <script src="/static/chatwidget.js"></script>
        <script>
            ChatWidget.init({
                apiUrl: window.location.origin,
                user_id: 'frank11',
                username: 'Frank',
                email: 'franklin@kambaa.com',
                device_id: 'Chrome 101',
                position: 'bottom-right',
                title: 'AI Assistant'
            });
        </script>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .info { background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Widget Test - Fixed Version</h1>
            <div class="info">
                <p><strong>✓ Fixed!</strong> This page tests the fixed chatwidget.js that properly handles DOM loading.</p>
                <p>The widget should appear in the bottom-right corner without any JavaScript errors.</p>
                <p>This demonstrates the fix for the "Cannot read properties of null (reading 'appendChild')" error.</p>
            </div>
        </div>
    </body>
    </html>
    '''

# System Prompt Management Routes
@app.route('/system_prompts', methods=['GET', 'POST'])
def system_prompts():
    """Handle system prompts management"""
    if request.method == 'GET':
        # Get all system prompts
        prompts = SystemPrompt.query.order_by(SystemPrompt.created_at.desc()).all()
        return jsonify({
            'prompts': [{
                'id': prompt.id,
                'name': prompt.name,
                'prompt_text': prompt.prompt_text,
                'is_active': prompt.is_active,
                'created_at': prompt.created_at.isoformat()
            } for prompt in prompts]
        })
    
    elif request.method == 'POST':
        # Create new system prompt
        try:
            data = request.get_json()
            
            name = data.get('name')
            prompt_text = data.get('prompt_text')
            is_active = data.get('is_active', False)
            
            if not name or not prompt_text:
                return jsonify({'error': 'Name and prompt text are required'}), 400
            
            # If setting as active, deactivate all others
            if is_active:
                SystemPrompt.query.update({'is_active': False})
            
            # Create new system prompt
            new_prompt = SystemPrompt(
                name=name,
                prompt_text=prompt_text,
                is_active=is_active
            )
            
            db.session.add(new_prompt)
            db.session.commit()
            
            return jsonify({'success': True, 'id': new_prompt.id})
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating system prompt: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/system_prompts/<int:prompt_id>', methods=['PUT', 'DELETE'])
def system_prompt_detail(prompt_id):
    """Handle individual system prompt operations"""
    prompt = SystemPrompt.query.get_or_404(prompt_id)
    
    if request.method == 'PUT':
        # Update system prompt
        try:
            data = request.get_json()
            
            prompt.name = data.get('name', prompt.name)
            prompt.prompt_text = data.get('prompt_text', prompt.prompt_text)
            is_active = data.get('is_active', False)
            
            # If setting as active, deactivate all others
            if is_active and not prompt.is_active:
                SystemPrompt.query.update({'is_active': False})
                prompt.is_active = True
            elif not is_active:
                prompt.is_active = False
            
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating system prompt: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        # Delete system prompt
        try:
            db.session.delete(prompt)
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting system prompt: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/system_prompts/<int:prompt_id>/activate', methods=['POST'])
def activate_system_prompt(prompt_id):
    """Activate a specific system prompt"""
    try:
        # Deactivate all prompts
        SystemPrompt.query.update({'is_active': False})
        
        # Activate the specified prompt
        prompt = SystemPrompt.query.get_or_404(prompt_id)
        prompt.is_active = True
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error activating system prompt: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Widget Icon Management API Endpoints
@app.route('/api/widget/icon', methods=['GET'])
def get_widget_icon():
    """Get current widget icon"""
    try:
        # Check for custom icon
        icon_path = os.path.join(WIDGET_ICON_FOLDER, 'widget_icon.png')
        if os.path.exists(icon_path):
            return jsonify({
                'iconUrl': f'{request.url_root}static/widget_icons/widget_icon.png',
                'isCustom': True
            })
        
        # Return default icon info
        return jsonify({
            'iconUrl': None,
            'isCustom': False
        })
    except Exception as e:
        logging.error(f"Error getting widget icon: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/widget/icon', methods=['POST'])
def upload_widget_icon():
    """Upload custom widget icon"""
    try:
        if 'iconFile' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['iconFile']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_image_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please use PNG, JPG, or SVG.'}), 400
        
        # Save the icon
        filename = 'widget_icon.png'
        file_path = os.path.join(WIDGET_ICON_FOLDER, filename)
        file.save(file_path)
        
        # Generate the icon URL
        icon_url = f'{request.url_root}static/widget_icons/{filename}'
        
        return jsonify({
            'success': True,
            'iconUrl': icon_url,
            'message': 'Icon uploaded successfully'
        })
    
    except Exception as e:
        logging.error(f"Error uploading widget icon: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/widget/icon', methods=['DELETE'])
def delete_widget_icon():
    """Reset to default widget icon"""
    try:
        icon_path = os.path.join(WIDGET_ICON_FOLDER, 'widget_icon.png')
        if os.path.exists(icon_path):
            os.remove(icon_path)
        
        return jsonify({
            'success': True,
            'message': 'Reset to default icon'
        })
    
    except Exception as e:
        logging.error(f"Error deleting widget icon: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===========================
# UNIFIED CONVERSATIONS ENDPOINTS
# ===========================

@app.route('/api/conversations')
def get_conversations():
    """Get all conversations (both chatbot and live chat)"""
    try:
        # Get query parameters
        conversation_type = request.args.get('type')  # 'chatbot', 'live_chat', or 'all'
        user_identifier = request.args.get('user')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = UnifiedConversation.query
        
        if conversation_type and conversation_type != 'all':
            query = query.filter_by(conversation_type=conversation_type)
        
        if user_identifier:
            query = query.filter_by(user_identifier=user_identifier)
        
        # Order by most recent first
        query = query.order_by(UnifiedConversation.last_activity.desc())
        
        # Apply pagination
        conversations = query.offset(offset).limit(limit).all()
        total_count = query.count()
        
        return jsonify({
            'conversations': [conv.to_dict() for conv in conversations],
            'total_count': total_count,
            'has_more': (offset + limit) < total_count
        })
        
    except Exception as e:
        logging.error(f"Error fetching conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<session_id>')
def get_conversation_detail(session_id):
    """Get detailed conversation with all messages"""
    try:
        conversation = UnifiedConversation.query.filter_by(session_id=session_id).first()
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get all messages for this conversation
        messages = UnifiedMessage.query.filter_by(session_id=session_id)\
            .order_by(UnifiedMessage.created_at.asc()).all()
        
        return jsonify({
            'conversation': conversation.to_dict(),
            'messages': [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        logging.error(f"Error fetching conversation detail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<session_id>/export')
def export_conversation(session_id):
    """Export conversation as JSON download"""
    try:
        conversation = UnifiedConversation.query.filter_by(session_id=session_id).first()
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get all messages
        messages = UnifiedMessage.query.filter_by(session_id=session_id)\
            .order_by(UnifiedMessage.created_at.asc()).all()
        
        export_data = {
            'conversation': conversation.to_dict(),
            'messages': [msg.to_dict() for msg in messages],
            'exported_at': datetime.utcnow().isoformat(),
            'export_version': '1.0'
        }
        
        # Create response with file download headers
        response = make_response(jsonify(export_data))
        response.headers['Content-Disposition'] = f'attachment; filename=conversation_{session_id}.json'
        response.headers['Content-Type'] = 'application/json'
        
        return response
        
    except Exception as e:
        logging.error(f"Error exporting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/stats')
def get_conversation_stats():
    """Get conversation statistics"""
    try:
        # Total conversations
        total_conversations = UnifiedConversation.query.count()
        chatbot_conversations = UnifiedConversation.query.filter_by(conversation_type='chatbot').count()
        live_chat_conversations = UnifiedConversation.query.filter_by(conversation_type='live_chat').count()
        
        # Active conversations (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_conversations = UnifiedConversation.query.filter(
            UnifiedConversation.last_activity >= yesterday
        ).count()
        
        # Total messages
        total_messages = UnifiedMessage.query.count()
        
        # Unique users
        unique_users = db.session.query(UnifiedConversation.user_identifier)\
            .distinct().count()
        
        return jsonify({
            'total_conversations': total_conversations,
            'chatbot_conversations': chatbot_conversations,
            'live_chat_conversations': live_chat_conversations,
            'active_conversations_24h': active_conversations,
            'total_messages': total_messages,
            'unique_users': unique_users
        })
        
    except Exception as e:
        logging.error(f"Error fetching conversation stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===========================
# RAG FEEDBACK ENDPOINTS
# ===========================

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a RAG response"""
    try:
        data = request.json
        
        # Extract feedback data
        session_id = data.get('session_id', str(uuid.uuid4()))
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        user_question = data.get('user_question', '')
        bot_response = data.get('bot_response', '')
        response_type = data.get('response_type', 'rag')
        feedback_type = data.get('feedback_type')  # 'thumbs_up' or 'thumbs_down'
        feedback_comment = data.get('feedback_comment', '')
        retrieved_chunks = data.get('retrieved_chunks')  # JSON string
        
        # Validate required fields
        if not all([user_question, bot_response, feedback_type]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: user_question, bot_response, feedback_type'
            }), 400
        
        if feedback_type not in ['thumbs_up', 'thumbs_down']:
            return jsonify({
                'status': 'error',
                'message': 'feedback_type must be "thumbs_up" or "thumbs_down"'
            }), 400
        
        # Create feedback record
        feedback = RagFeedback(
            session_id=session_id,
            user_id=user_id,
            username=username,
            email=email,
            user_question=user_question,
            bot_response=bot_response,
            response_type=response_type,
            feedback_type=feedback_type,
            feedback_comment=feedback_comment,
            retrieved_chunks=retrieved_chunks
        )
        
        # Save to database
        db.session.add(feedback)
        db.session.commit()
        
        logging.info(f"Feedback saved: {feedback_type} for session {session_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Thank you for your feedback! It will help us improve the system.',
            'feedback_id': feedback.id
        })
        
    except Exception as e:
        logging.error(f"Error saving feedback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error saving feedback. Please try again.'
        }), 500

@app.route('/feedback', methods=['GET'])
def get_feedback():
    """Get all feedback records (admin endpoint)"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        feedback_type = request.args.get('feedback_type')  # Filter by feedback type
        used_for_training = request.args.get('used_for_training')  # Filter by training status
        
        # Build query
        query = RagFeedback.query.order_by(RagFeedback.feedback_timestamp.desc())
        
        if feedback_type:
            query = query.filter(RagFeedback.feedback_type == feedback_type)
        
        if used_for_training is not None:
            query = query.filter(RagFeedback.used_for_training == (used_for_training.lower() == 'true'))
        
        # Apply pagination
        total_count = query.count()
        feedback_records = query.offset(offset).limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'feedback': [record.to_dict() for record in feedback_records],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logging.error(f"Error getting feedback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving feedback records'
        }), 500

@app.route('/feedback/<int:feedback_id>', methods=['PUT'])
def update_feedback(feedback_id):
    """Update feedback record (mark as used for training, add notes)"""
    try:
        data = request.json
        feedback = RagFeedback.query.get(feedback_id)
        
        if not feedback:
            return jsonify({
                'status': 'error',
                'message': 'Feedback record not found'
            }), 404
        
        # Update fields
        if 'used_for_training' in data:
            feedback.used_for_training = data['used_for_training']
        
        if 'training_notes' in data:
            feedback.training_notes = data['training_notes']
            
        # New response analysis fields
        if 'response_category' in data:
            feedback.response_category = data['response_category']
            
        if 'improvement_suggestions' in data:
            feedback.improvement_suggestions = data['improvement_suggestions']
            
        if 'admin_notes' in data:
            feedback.admin_notes = data['admin_notes']
            
        if 'training_priority' in data:
            feedback.training_priority = data['training_priority']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback record updated successfully',
            'feedback': feedback.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error updating feedback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error updating feedback record'
        }), 500

@app.route('/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics for analytics"""
    try:
        total_feedback = RagFeedback.query.count()
        thumbs_up = RagFeedback.query.filter(RagFeedback.feedback_type == 'thumbs_up').count()
        thumbs_down = RagFeedback.query.filter(RagFeedback.feedback_type == 'thumbs_down').count()
        used_for_training = RagFeedback.query.filter(RagFeedback.used_for_training == True).count()
        
        # Calculate satisfaction rate
        satisfaction_rate = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        
        # Get feedback by response type
        response_types = db.session.query(
            RagFeedback.response_type,
            db.func.count(RagFeedback.id).label('count')
        ).group_by(RagFeedback.response_type).all()
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total_feedback': total_feedback,
                'thumbs_up': thumbs_up,
                'thumbs_down': thumbs_down,
                'satisfaction_rate': round(satisfaction_rate, 2),
                'used_for_training': used_for_training,
                'response_types': {rt[0]: rt[1] for rt in response_types}
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting feedback stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving feedback statistics'
        }), 500

# Chat Settings API endpoints
@app.route('/chat_settings', methods=['GET'])
def get_chat_settings():
    """Get all chat settings"""
    try:
        settings = ChatSettings.query.all()
        settings_dict = {}
        for setting in settings:
            if setting.setting_type == 'boolean':
                settings_dict[setting.setting_name] = setting.setting_value.lower() in ('true', '1', 'yes')
            elif setting.setting_type == 'integer':
                try:
                    settings_dict[setting.setting_name] = int(setting.setting_value)
                except ValueError:
                    settings_dict[setting.setting_name] = 0
            elif setting.setting_type == 'json':
                try:
                    settings_dict[setting.setting_name] = json.loads(setting.setting_value)
                except json.JSONDecodeError:
                    settings_dict[setting.setting_name] = {}
            else:
                settings_dict[setting.setting_name] = setting.setting_value
        
        # Add defaults for required settings
        defaults = {
            'typing_effect_enabled': True,
            'typing_effect_speed': 25,  # milliseconds per character
            'auto_scroll_during_typing': False
        }
        
        for key, default_value in defaults.items():
            if key not in settings_dict:
                settings_dict[key] = default_value
                # Create the setting in database
                setting_type = 'boolean' if isinstance(default_value, bool) else 'integer'
                ChatSettings.set_setting(key, default_value, setting_type)
        
        return jsonify({'success': True, 'settings': settings_dict})
        
    except Exception as e:
        logging.error(f"Error getting chat settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat_settings', methods=['POST'])
def update_chat_settings():
    """Update chat settings"""
    try:
        data = request.get_json()
        
        # Define allowed settings and their types
        allowed_settings = {
            'typing_effect_enabled': 'boolean',
            'typing_effect_speed': 'integer',
            'auto_scroll_during_typing': 'boolean'
        }
        
        updated_settings = {}
        for key, value in data.items():
            if key in allowed_settings:
                setting_type = allowed_settings[key]
                ChatSettings.set_setting(key, value, setting_type)
                updated_settings[key] = value
        
        return jsonify({
            'success': True, 
            'message': 'Chat settings updated successfully',
            'updated_settings': updated_settings
        })
        
    except Exception as e:
        logging.error(f"Error updating chat settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat_settings/<setting_name>', methods=['GET'])
def get_chat_setting(setting_name):
    """Get a specific chat setting"""
    try:
        setting = ChatSettings.query.filter_by(setting_name=setting_name).first()
        if not setting:
            return jsonify({'success': False, 'error': 'Setting not found'}), 404
        
        value = ChatSettings.get_setting(setting_name)
        return jsonify({
            'success': True, 
            'setting': {
                'name': setting_name,
                'value': value,
                'type': setting.setting_type,
                'description': setting.description
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting chat setting {setting_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Response Template Management Endpoints
@app.route('/response_templates', methods=['GET'])
def get_response_templates():
    """Get all response templates"""
    try:
        templates = ResponseTemplate.query.order_by(ResponseTemplate.priority.desc()).all()
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates]
        })
    except Exception as e:
        logging.error(f"Error getting response templates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/response_templates', methods=['POST'])
def create_response_template():
    """Create a new response template"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'template_text', 'category']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        template = ResponseTemplate(
            name=data['name'],
            description=data.get('description', ''),
            trigger_keywords=data.get('trigger_keywords', []),
            question_patterns=data.get('question_patterns', []),
            categories=data.get('categories', [data['category']]),
            template_text=data['template_text'],
            fallback_response=data.get('fallback_response'),
            priority=data.get('priority', 0),
            is_active=data.get('is_active', True),
            requires_context=data.get('requires_context', False),
            created_by=data.get('created_by', 'admin')
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Response template created successfully',
            'template': template.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error creating response template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/response_templates/<int:template_id>', methods=['PUT'])
def update_response_template(template_id):
    """Update response template"""
    try:
        data = request.get_json()
        template = ResponseTemplate.query.get(template_id)
        
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Update fields if provided
        if 'name' in data:
            template.name = data['name']
        if 'description' in data:
            template.description = data['description']
        if 'trigger_keywords' in data:
            template.trigger_keywords = data['trigger_keywords']
        if 'question_patterns' in data:
            template.question_patterns = data['question_patterns']
        if 'categories' in data:
            template.categories = data['categories']
        if 'template_text' in data:
            template.template_text = data['template_text']
        if 'fallback_response' in data:
            template.fallback_response = data['fallback_response']
        if 'priority' in data:
            template.priority = data['priority']
        if 'is_active' in data:
            template.is_active = data['is_active']
        if 'requires_context' in data:
            template.requires_context = data['requires_context']
        
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Response template updated successfully',
            'template': template.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error updating response template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/response_templates/<int:template_id>', methods=['DELETE'])
def delete_response_template(template_id):
    """Delete response template"""
    try:
        template = ResponseTemplate.query.get(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Response template deleted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error deleting response template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/feedback/<int:feedback_id>/analyze', methods=['POST'])
def analyze_feedback_response(feedback_id):
    """Analyze a feedback response and suggest improvements"""
    try:
        data = request.get_json()
        feedback = RagFeedback.query.get(feedback_id)
        
        if not feedback:
            return jsonify({'success': False, 'error': 'Feedback not found'}), 404
        
        # Update analysis fields
        if 'response_category' in data:
            feedback.response_category = data['response_category']
        if 'improvement_suggestions' in data:
            feedback.improvement_suggestions = data['improvement_suggestions']
        if 'admin_notes' in data:
            feedback.admin_notes = data['admin_notes']
        if 'training_priority' in data:
            feedback.training_priority = data['training_priority']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Feedback analysis saved successfully',
            'feedback': feedback.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error analyzing feedback: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

from datetime import datetime

# Global log storage for the admin panel
admin_logs = []

class AdminLogHandler(logging.Handler):
    """Custom log handler to capture logs for the admin panel"""
    def emit(self, record):
        global admin_logs
        try:
            # Format the log entry
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
                'level': record.levelname,
                'message': record.getMessage(),
                'response_type': getattr(record, 'response_type', 'SYSTEM')
            }
            
            # Add to the beginning of the list (newest first)
            admin_logs.insert(0, log_entry)
            
            # Keep only the last 1000 logs to prevent memory issues
            if len(admin_logs) > 1000:
                admin_logs = admin_logs[:1000]
                
        except Exception:
            pass  # Don't let log handler errors break the application

# Set up the admin log handler
admin_handler = AdminLogHandler()
admin_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(admin_handler)

@app.route('/logs', methods=['GET'])
def get_system_logs():
    """Get system logs for the admin panel"""
    try:
        from datetime import datetime, timedelta
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        level_filter = request.args.get('level', '')
        response_type_filter = request.args.get('response_type', '')
        search_query = request.args.get('search', '')
        
        # Get logs from our global storage
        log_entries = list(admin_logs)  # Make a copy
        
        # Apply filters
        if level_filter:
            log_entries = [log for log in log_entries if log['level'] == level_filter]
        
        if response_type_filter:
            log_entries = [log for log in log_entries if response_type_filter in log.get('response_type', '')]
        
        if search_query:
            log_entries = [log for log in log_entries if search_query.lower() in log['message'].lower()]
        
        # Limit results
        log_entries = log_entries[:limit]
        
        return jsonify({
            'success': True,
            'logs': log_entries,
            'total_count': len(log_entries)
        })
            
    except Exception as e:
        logging.error(f"Error getting system logs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== AGENT PORTAL ENDPOINTS ====================

@app.route('/agent_portal')
def agent_portal():
    """Agent portal interface with chatbot and live chat tabs"""
    return render_template('agent_portal_tabs.html')

@app.route('/api/chatbot/conversations', methods=['GET'])
def get_chatbot_conversations():
    """Get all chatbot conversations"""
    try:
        from models import UnifiedConversation
        
        # Query unified conversations that are chatbot type
        conversations = UnifiedConversation.query.filter_by(
            conversation_type='chatbot'
        ).order_by(UnifiedConversation.updated_at.desc()).limit(100).all()
        
        # Format for display
        chatbot_sessions = []
        for conv in conversations:
            # Get message count
            from models import UnifiedMessage
            message_count = UnifiedMessage.query.filter_by(session_id=conv.session_id).count()
            
            chatbot_sessions.append({
                'session_id': conv.session_id,
                'user_identifier': conv.user_identifier,
                'username': conv.username or 'Anonymous',
                'email': conv.email or 'Not provided',
                'device_id': conv.device_id or 'Unknown device',
                'message_count': message_count,
                'created_at': conv.created_at.isoformat() if conv.created_at else '',
                'updated_at': conv.updated_at.isoformat() if conv.updated_at else '',
                'last_activity': conv.updated_at.strftime('%Y-%m-%d %H:%M:%S') if conv.updated_at else 'Unknown',
                'tags': conv.get_tags()  # Include tags for filtering
            })
        
        return jsonify({
            'success': True,
            'conversations': chatbot_sessions,
            'total_count': len(chatbot_sessions)
        })
        
    except Exception as e:
        logging.error(f"Error getting chatbot conversations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chatbot/conversations/<session_id>/messages', methods=['GET'])
def get_chatbot_conversation_messages(session_id):
    """Get messages for a specific chatbot conversation"""
    try:
        from models import UnifiedMessage
        
        # Get messages from unified conversation system
        messages = UnifiedMessage.query.filter_by(session_id=session_id).order_by(UnifiedMessage.created_at.asc()).all()
        
        # Format messages for display
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': msg.id,
                'session_id': session_id,
                'message_content': msg.message_content,
                'sender_type': msg.sender_type,
                'sender_name': msg.sender_name or msg.sender_type,
                'created_at': msg.created_at.isoformat() if msg.created_at else '',
                'timestamp': msg.created_at.strftime('%H:%M:%S') if msg.created_at else ''
            })
        
        return jsonify({
            'success': True,
            'messages': formatted_messages,
            'total_count': len(formatted_messages)
        })
        
    except Exception as e:
        logging.error(f"Error getting chatbot conversation messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== LIVE CHAT ENDPOINTS ====================

@app.route('/api/live_chat/sessions', methods=['GET'])
def get_live_chat_sessions():
    """Get live chat sessions for agent dashboard using unified conversations"""
    try:
        from models import UnifiedConversation
        
        status = request.args.get('status', 'all')
        agent_id = request.args.get('agent_id')
        
        # Query unified conversations that are live chat type
        query = UnifiedConversation.query.filter_by(conversation_type='live_chat')
        
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        
        conversations = query.order_by(UnifiedConversation.updated_at.desc()).limit(50).all()
        
        # Convert to live chat session format for compatibility
        sessions = []
        for conv in conversations:
            sessions.append({
                'session_id': conv.session_id,
                'user_identifier': conv.user_identifier,
                'username': conv.username,
                'email': conv.email,
                'device_id': conv.device_id,
                'status': 'active',  # Simplified status
                'agent_id': conv.agent_id,
                'priority': 'normal',
                'department': 'support',
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'initial_message': 'Live chat session'
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions
        })
        
    except Exception as e:
        logging.error(f"Error getting live chat sessions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get messages for a specific live chat session using unified conversation system"""
    try:
        from models import UnifiedMessage
        
        # Get messages from unified conversation system
        messages = UnifiedMessage.query.filter_by(session_id=session_id).order_by(UnifiedMessage.created_at.asc()).all()
        
        # Convert to live chat format for compatibility
        live_chat_messages = []
        for msg in messages:
            live_chat_messages.append({
                'id': msg.id,
                'session_id': session_id,
                'message_content': msg.message_content,
                'sender_type': msg.sender_type,
                'sender_name': msg.sender_name,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat(),
                'metadata': msg.get_metadata()
            })
        
        return jsonify({
            'success': True,
            'messages': live_chat_messages
        })
        
    except Exception as e:
        logging.error(f"Error getting session messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/sessions/<session_id>/messages', methods=['POST'])
def send_session_message(session_id):
    """Send a message in a live chat session"""
    try:
        from live_chat_manager import live_chat_manager
        data = request.json
        
        message = live_chat_manager.send_message(
            session_id=session_id,
            sender_type=data['sender_type'],
            sender_id=data['sender_id'],
            message_content=data['message_content'],
            sender_name=data.get('sender_name'),
            message_type=data.get('message_type', 'text'),
            metadata=data.get('metadata', {})
        )
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error sending session message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/sessions/<session_id>/status', methods=['PUT'])
def update_session_status(session_id):
    """Update live chat session status"""
    try:
        from live_chat_manager import live_chat_manager
        data = request.json
        
        success = live_chat_manager.update_session_status(session_id, data['status'])
        
        return jsonify({
            'success': success,
            'message': f"Session status updated to {data['status']}" if success else "Session not found"
        })
        
    except Exception as e:
        logging.error(f"Error updating session status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/sessions/<session_id>/send_message', methods=['POST'])
def send_live_chat_message(session_id):
    """Send a message in a live chat session using unified conversation system"""
    try:
        from models import UnifiedConversation, UnifiedMessage
        import uuid
        data = request.json
        
        # Find the unified conversation
        conversation = UnifiedConversation.query.filter_by(session_id=session_id).first()
        if not conversation:
            return jsonify({'success': False, 'error': 'Conversation not found'}), 404
        
        # Determine sender type and content
        sender_type = data.get('sender_type', 'agent')
        message_content = data.get('message_content', data.get('message', ''))
        sender_name = data.get('sender_name', 'Agent' if sender_type == 'agent' else 'User')
        
        # Create unified message
        message = UnifiedMessage(
            session_id=session_id,
            message_id=f"live_{uuid.uuid4().hex[:12]}",
            sender_type=sender_type,
            sender_name=sender_name,
            message_content=message_content,
            message_type='text',
            created_at=datetime.utcnow()
        )
        
        db.session.add(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        if sender_type == 'agent' and not conversation.agent_id:
            conversation.agent_id = data.get('sender_id', 'agent')
        
        db.session.commit()
        
        logging.info(f"Live chat message sent in session {session_id} by {sender_type}")
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'session_id': session_id,
                'content': message_content,
                'sender': sender_name,
                'sender_type': sender_type,
                'created_at': message.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"Error sending live chat message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/transfer_to_agent', methods=['POST'])
def transfer_to_agent():
    """Transfer a chatbot conversation to live agent using unified conversation system"""
    try:
        from live_chat_manager import live_chat_manager
        from models import UnifiedConversation, UnifiedMessage
        from datetime import datetime
        import uuid
        data = request.json
        
        user_identifier = data.get('user_identifier', 'anonymous')
        session_id = data.get('session_id')
        
        # Find existing unified conversation for this user
        existing_conversation = UnifiedConversation.query.filter_by(
            session_id=session_id,
            user_identifier=user_identifier
        ).first()
        
        if existing_conversation:
            # Update existing conversation to live chat type
            existing_conversation.conversation_type = 'live_chat'
            existing_conversation.agent_id = None  # Will be assigned when agent connects
            existing_conversation.updated_at = datetime.utcnow()
            
            # Add transfer message to existing conversation
            transfer_message = UnifiedMessage(
                session_id=session_id,
                message_type='system',
                message_content=f"Chat transferred to live agent: {data.get('initial_message', 'User requested live chat')}",
                sender_type='system',
                sender_name='System',
                message_id=f"transfer_{uuid.uuid4().hex[:12]}",
                created_at=datetime.utcnow()
            )
            
            db.session.add(transfer_message)
            db.session.commit()
            
            logging.info(f"Transferred existing conversation {session_id} to live chat for user {user_identifier}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Chat transferred to live agent. You will be connected shortly.',
                'conversation_continued': True
            })
        else:
            # Fallback: Create new live chat session if no existing conversation found
            session = live_chat_manager.create_session(
                user_identifier=user_identifier,
                username=data.get('username'),
                email=data.get('email'),
                initial_message=data.get('initial_message'),
                department=data.get('department'),
                priority=data.get('priority', 'normal')
            )
            
            # Import previous conversation history if provided
            conversation_history = data.get('conversation_history', [])
            if conversation_history:
                live_chat_manager.import_bot_conversation(session.session_id, conversation_history)
            
            return jsonify({
                'success': True,
                'session_id': session.session_id,
                'message': 'Chat transferred to live agent. You will be connected shortly.',
                'imported_messages': len(conversation_history),
                'conversation_continued': False
            })
        
    except Exception as e:
        logging.error(f"Error transferring to agent: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/agents', methods=['GET'])
def get_live_chat_agents():
    """Get live chat agents"""
    try:
        agents = LiveChatAgent.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'agents': [agent.to_dict() for agent in agents]
        })
        
    except Exception as e:
        logging.error(f"Error getting live chat agents: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/agents', methods=['POST'])
def create_live_chat_agent():
    """Create a new live chat agent"""
    try:
        data = request.json
        
        agent = LiveChatAgent(
            agent_id=data.get('agent_id', f"agent_{uuid.uuid4().hex[:8]}"),
            agent_name=data['agent_name'],
            email=data.get('email'),
            department=data.get('department'),
            max_concurrent_chats=data.get('max_concurrent_chats', 5)
        )
        
        if data.get('skills'):
            agent.set_skills(data['skills'])
        
        db.session.add(agent)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'agent': agent.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error creating live chat agent: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live_chat/agents/<agent_id>/status', methods=['PUT'])
def update_agent_status(agent_id):
    """Update agent status"""
    try:
        from live_chat_manager import live_chat_manager
        data = request.json
        
        success = live_chat_manager.update_agent_status(agent_id, data['status'])
        
        return jsonify({
            'success': success,
            'message': f"Agent status updated to {data['status']}" if success else "Agent not found"
        })
        
    except Exception as e:
        logging.error(f"Error updating agent status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WEBHOOK MANAGEMENT ENDPOINTS ====================

@app.route('/api/webhooks', methods=['GET'])
def get_webhooks():
    """Get all webhook configurations"""
    try:
        webhooks = WebhookConfig.query.all()
        
        return jsonify({
            'success': True,
            'webhooks': [webhook.to_dict() for webhook in webhooks]
        })
        
    except Exception as e:
        logging.error(f"Error getting webhooks: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/webhooks', methods=['POST'])
def create_webhook():
    """Create a new webhook configuration"""
    try:
        data = request.json
        
        webhook = WebhookConfig(
            name=data['name'],
            provider=data['provider'],
            webhook_url=data['webhook_url'],
            webhook_secret=data.get('webhook_secret'),
            auth_type=data.get('auth_type', 'none'),
            retry_count=data.get('retry_count', 3),
            timeout_seconds=data.get('timeout_seconds', 30)
        )
        
        webhook.set_event_types(data.get('event_types', []))
        webhook.set_headers(data.get('headers', {}))
        webhook.set_auth_credentials(data.get('auth_credentials', {}))
        
        db.session.add(webhook)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'webhook': webhook.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Error creating webhook: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/webhooks/<int:webhook_id>/test', methods=['POST'])
def test_webhook(webhook_id):
    """Test a webhook configuration"""
    try:
        from webhook_manager import webhook_manager
        
        webhook = WebhookConfig.query.get_or_404(webhook_id)
        result = webhook_manager.test_webhook(webhook)
        
        return jsonify({
            'success': True,
            'test_result': result
        })
        
    except Exception as e:
        logging.error(f"Error testing webhook: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# Import webhook integration
try:
    from webhook_integration import webhook_integration
except ImportError:
    webhook_integration = None

# Webhook Integration Routes
@app.route('/api/webhook/incoming', methods=['POST'])
def webhook_incoming():
    """Receive messages from third-party platforms"""
    try:
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        if not webhook_integration:
            return jsonify({
                'success': False,
                'error': 'Webhook integration not available'
            }), 500
        
        # Load webhook integration
        webhook_integration.load_config()
        
        # Process the incoming message
        result = webhook_integration.process_incoming_message(webhook_data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/webhook/config', methods=['GET', 'POST'])
def webhook_config():
    """Get or update webhook configuration"""
    if request.method == 'GET':
        try:
            configs = WebhookConfig.query.all()
            return jsonify({
                'success': True,
                'configs': [config.to_dict() for config in configs]
            })
        except Exception as e:
            logger.error(f"Error getting webhook configs: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Handle different actions
            action = data.get('action')
            
            if action == 'activate':
                config_id = data.get('config_id')
                if not config_id:
                    return jsonify({
                        'success': False,
                        'error': 'config_id is required for activation'
                    }), 400
                
                # Deactivate all configs first
                WebhookConfig.query.update({'is_active': False})
                
                # Activate the specified config
                config = WebhookConfig.query.get(config_id)
                if not config:
                    return jsonify({
                        'success': False,
                        'error': 'Webhook configuration not found'
                    }), 404
                
                config.is_active = True
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Webhook activated successfully'
                })
            
            elif action == 'deactivate':
                config_id = data.get('config_id')
                if config_id:
                    # Deactivate specific config
                    config = WebhookConfig.query.get(config_id)
                    if not config:
                        return jsonify({
                            'success': False,
                            'error': 'Webhook configuration not found'
                        }), 404
                    
                    config.is_active = False
                    db.session.commit()
                else:
                    # Deactivate all configs
                    WebhookConfig.query.update({'is_active': False})
                    db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Webhook deactivated successfully'
                })
            
            elif action == 'deactivate_all':
                # Deactivate all configs
                WebhookConfig.query.update({'is_active': False})
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'All webhooks deactivated successfully'
                })
            
            else:
                # Default behavior: Create new webhook config
                # Validate required fields
                required_fields = ['name', 'provider']
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {missing_fields}'
                    }), 400
                
                # Deactivate other configs if this one is set as active
                if data.get('is_active', False):
                    WebhookConfig.query.update({'is_active': False})
                
                # Create new webhook config
                config = WebhookConfig(
                    name=data['name'],
                    provider=data['provider'],
                    webhook_url=data.get('outgoing_webhook_url', data.get('webhook_url', '')),
                    timeout_seconds=data.get('timeout_seconds', 30),
                    retry_count=data.get('retry_attempts', 3),
                    is_active=data.get('is_active', False),
                    event_types='["message"]'  # Default event types
                )
                
                # Set custom headers if provided
                if 'custom_headers' in data:
                    config.set_headers(data['custom_headers'])
                
                # Set auth token if provided
                if 'auth_token' in data:
                    config.set_auth_credentials({'token': data['auth_token']})
                
                db.session.add(config)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'config': config.to_dict()
                })
            
        except Exception as e:
            logging.error(f"Error creating webhook config: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500


@app.route('/api/webhook/messages', methods=['GET'])
def webhook_messages():
    """Get webhook message history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        platform = request.args.get('platform')
        message_type = request.args.get('message_type')
        status = request.args.get('status')
        
        query = WebhookMessage.query
        
        if platform:
            query = query.filter(WebhookMessage.platform == platform)
        if message_type:
            query = query.filter(WebhookMessage.message_type == message_type)
        if status:
            query = query.filter(WebhookMessage.status == status)
        
        messages = query.order_by(WebhookMessage.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages.items],
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        })
        
    except Exception as e:
        logging.error(f"Error getting webhook messages: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/webhook/config/<int:config_id>', methods=['DELETE'])
def delete_webhook_config(config_id):
    """Delete a webhook configuration"""
    try:
        config = WebhookConfig.query.get(config_id)
        if not config:
            return jsonify({
                'success': False,
                'error': 'Webhook configuration not found'
            }), 404
        
        db.session.delete(config)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Webhook configuration deleted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error deleting webhook config: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


# ===========================
# VOICE AGENT ENDPOINTS
# ===========================

@app.route('/api/voice/synthesize', methods=['POST'])
def synthesize_voice():
    """Convert text to speech using Kokoro TTS"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        voice = data.get('voice', 'af_heart')  # Default to American female voice
        
        # Synthesize speech using local VoiceAgent instance
        from voice_agent import VoiceAgent
        local_voice_agent = VoiceAgent()
        result = local_voice_agent.synthesize_speech(text, voice)
        
        if result and result.get('success'):
            # Return audio file for download
            from flask import send_file
            audio_file = result['audio_file']
            engine = result.get('engine', 'unknown')
            
            # Determine file extension and mimetype based on engine
            if engine == 'gtts':
                mimetype = 'audio/mp3'
                filename = f'speech_{uuid.uuid4().hex[:8]}.mp3'
            else:
                mimetype = 'audio/wav'  
                filename = f'speech_{uuid.uuid4().hex[:8]}.wav'
            
            return send_file(
                audio_file,
                as_attachment=True,
                download_name=filename,
                mimetype=mimetype
            )
        else:
            error_msg = result.get('error', 'Speech synthesis failed') if result else 'Speech synthesis failed'
            logging.error(f"Voice synthesis failed: {error_msg}")
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        logging.error(f"Error in voice synthesis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/voice/available_voices', methods=['GET'])
def get_available_voices():
    """Get list of available TTS voices"""
    try:
        voices = voice_agent.get_available_voices()
        return jsonify({
            'success': True,
            'voices': voices
        })
    except Exception as e:
        logging.error(f"Error getting available voices: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/voice/ask', methods=['POST'])
def voice_ask():
    """Enhanced ask endpoint that can return both text and voice response"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Extract user parameters if provided
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        device_id = data.get('device_id')
        voice_enabled = data.get('voice_enabled', False)
        selected_voice = data.get('voice', 'af_heart')
        
        # Determine user identifier (priority: user_id > email > device_id)
        user_identifier = user_id or email or device_id
        
        # Get or create session ID for fallback
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        # Log the request with user context
        if user_identifier:
            logging.info(f"Voice-enabled question for user: {user_identifier} (username: {username})")
        else:
            logging.info(f"Voice-enabled question for session: {session_id}")
        
        # Use existing RAG chain for answer generation
        rag_chain = RAGChain()
        answer = rag_chain.get_answer(
            question=question,
            index_folder='faiss_index',
            session_id=session_id,
            user_identifier=user_identifier,
            username=username,
            email=email,
            device_id=device_id
        )
        
        response_data = {
            'answer': answer,
            'status': 'success',
            'response_type': 'rag_with_ai_tools',
            'user_info': {
                'user_id': user_identifier,
                'username': username,
                'email': email,
                'device_id': device_id,
                'session_type': 'persistent' if user_identifier else 'temporary'
            }
        }
        
        # If voice is enabled, also generate speech
        if voice_enabled:
            speech_result = voice_agent.synthesize_speech(answer, selected_voice)
            if speech_result and speech_result.get('success'):
                response_data['voice_data'] = {
                    'audio_file': speech_result['audio_file'],
                    'voice_used': speech_result['voice_used'],
                    'duration': speech_result['duration']
                }
        
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error in voice ask endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/voice/cleanup/<path:filename>', methods=['DELETE'])
def cleanup_voice_file(filename):
    """Clean up temporary voice files"""
    try:
        import tempfile
        file_path = os.path.join(tempfile.gettempdir(), filename)
        success = voice_agent.cleanup_temp_file(file_path)
        return jsonify({'success': success})
    except Exception as e:
        logging.error(f"Error cleaning up voice file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ElevenLabs Voice Agent Routes
@app.route('/api/elevenlabs/voice', methods=['POST'])
def elevenlabs_voice_chat():
    """ElevenLabs voice chat endpoint"""
    from elevenlabs_agent import handle_elevenlabs_voice_request
    return handle_elevenlabs_voice_request()

@app.route('/api/elevenlabs/voices', methods=['GET'])
def elevenlabs_voices():
    """Get available ElevenLabs voices"""
    try:
        from elevenlabs_agent import ElevenLabsVoiceAgent
        agent = ElevenLabsVoiceAgent()
        # Return a basic voice info since we don't have the method implemented
        return jsonify({
            'success': True,
            'voices': [
                {
                    'voice_id': '21m00Tcm4TlvDq8ikWAM',
                    'name': 'Rachel (Default)',
                    'category': 'premade'
                }
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/update_elevenlabs_key', methods=['POST'])
def update_elevenlabs_key():
    """Update ElevenLabs API key in environment"""
    try:
        api_key = request.form.get('elevenlabs_key', '').strip()
        
        if not api_key:
            flash('API key cannot be empty', 'error')
            return redirect(url_for('admin'))
        
        # Save to environment
        import os
        os.environ['ELEVENLABS_API_KEY'] = api_key
        
        # Test the API key by trying to get voices
        try:
            from elevenlabs_agent import ElevenLabsVoiceAgent
            agent = ElevenLabsVoiceAgent()
            # Test the API key with a simple validation
            flash('ElevenLabs API key updated successfully!', 'success')
        except Exception as e:
            flash(f'API key saved but validation failed: {str(e)}', 'warning')
        
        return redirect(url_for('admin'))
        
    except Exception as e:
        logger.error(f"Error updating ElevenLabs key: {e}")
        flash(f'Error updating API key: {str(e)}', 'error')
        return redirect(url_for('admin'))

@app.route('/api/elevenlabs/status')
def elevenlabs_status():
    """Check ElevenLabs API status"""
    try:
        import os
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        
        if not api_key:
            return jsonify({
                'success': True,
                'status': 'no_key',
                'message': 'No API key configured'
            })
        
        # Test the API key
        try:
            from elevenlabs_agent import ElevenLabsVoiceAgent
            agent = ElevenLabsVoiceAgent()
            # If agent initializes successfully, the key is valid
            return jsonify({
                'success': True,
                'status': 'active',
                'message': 'Connected - ElevenLabs API key is valid',
                'voice_count': 1
            })
        except Exception as init_error:
            return jsonify({
                'success': True,
                'status': 'error',
                'message': f'API Key Error: {str(init_error)}'
            })
        
    except Exception as e:
        return jsonify({
            'success': True,
            'status': 'error',
            'message': f'API Error: {str(e)}'
        })

@app.route('/api/elevenlabs/agents', methods=['GET'])
def list_elevenlabs_agents():
    """List all ElevenLabs agents"""
    try:
        result = embedded_agent.list_agents()
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logging.error(f"Error listing ElevenLabs agents: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/elevenlabs/agent/create', methods=['POST'])
def create_elevenlabs_agent():
    """Create a new ElevenLabs agent programmatically"""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'Apna Voice Assistant')
        system_prompt = data.get('system_prompt')
        
        result = embedded_agent.create_agent_programmatically(name, system_prompt)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logging.error(f"Error creating ElevenLabs agent: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/elevenlabs/signed_url', methods=['POST'])
def get_elevenlabs_signed_url():
    """Get signed URL for dashboard-created agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'})
        
        result = embedded_agent.get_signed_url(agent_id)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logging.error(f"Error getting ElevenLabs signed URL: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/elevenlabs/conversation/end', methods=['POST'])
def end_elevenlabs_conversation():
    """End current ElevenLabs conversation"""
    try:
        embedded_agent.end_conversation()
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error ending ElevenLabs conversation: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_elevenlabs_embedded')
def test_elevenlabs_embedded():
    """Test page for ElevenLabs embedded voice agent"""
    with open('test_elevenlabs_embedded.html', 'r') as f:
        return f.read()






if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
