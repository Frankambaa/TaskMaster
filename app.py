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
from models import db, ApiRule, ApiTool, UserConversation, SystemPrompt, RagFeedback, ChatSettings, ResponseTemplate
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
        
        # Get or create session ID for fallback
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        # Log the request with user context
        if user_identifier:
            logging.info(f"Processing question for user: {user_identifier} (username: {username})")
        else:
            logging.info(f"Processing question for session: {session_id}")
        
        # Use RAG chain with AI-driven tool selection and persistent memory
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
