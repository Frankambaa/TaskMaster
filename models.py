from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

# Database configuration
db = SQLAlchemy()

class UserConversation(db.Model):
    """Model for storing user conversation history"""
    __tablename__ = 'user_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_identifier = db.Column(db.String(255), nullable=False, index=True)  # user_id, email, or device_id
    username = db.Column(db.String(255), nullable=True)  # Optional username for display
    email = db.Column(db.String(255), nullable=True)  # Optional email
    device_id = db.Column(db.String(255), nullable=True)  # Optional device identifier
    conversation_data = db.Column(db.Text, nullable=False)  # JSON-encoded conversation history
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserConversation {self.user_identifier}>'
    
    def get_conversation_history(self):
        """Return conversation history as list of messages"""
        try:
            return json.loads(self.conversation_data) if self.conversation_data else []
        except json.JSONDecodeError:
            return []
    
    def set_conversation_history(self, messages):
        """Set conversation history from list of messages"""
        self.conversation_data = json.dumps(messages)
        self.last_activity = datetime.utcnow()
    
    def add_message(self, message_type, content):
        """Add a single message to conversation history"""
        history = self.get_conversation_history()
        history.append({
            'type': message_type,  # 'human' or 'ai'
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.set_conversation_history(history)
    
    def clear_conversation(self):
        """Clear all conversation history"""
        self.conversation_data = json.dumps([])
        self.last_activity = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_identifier': self.user_identifier,
            'username': self.username,
            'email': self.email,
            'device_id': self.device_id,
            'last_activity': self.last_activity.isoformat(),
            'created_at': self.created_at.isoformat(),
            'message_count': len(self.get_conversation_history())
        }

class ChatSettings(db.Model):
    """Model for storing chat widget configuration settings"""
    __tablename__ = 'chat_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(255), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    setting_type = db.Column(db.String(50), default='string')  # string, boolean, integer, json
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_setting(name, default_value=None):
        """Get a setting value by name"""
        setting = ChatSettings.query.filter_by(setting_name=name).first()
        if not setting:
            return default_value
            
        if setting.setting_type == 'boolean':
            return setting.setting_value.lower() in ('true', '1', 'yes')
        elif setting.setting_type == 'integer':
            try:
                return int(setting.setting_value)
            except ValueError:
                return default_value
        elif setting.setting_type == 'json':
            try:
                return json.loads(setting.setting_value)
            except json.JSONDecodeError:
                return default_value
        else:
            return setting.setting_value
    
    @staticmethod
    def set_setting(name, value, setting_type='string', description=None):
        """Set or update a setting"""
        setting = ChatSettings.query.filter_by(setting_name=name).first()
        
        # Convert value to string for storage
        if setting_type == 'boolean':
            str_value = str(bool(value)).lower()
        elif setting_type in ('integer', 'json'):
            str_value = str(value) if setting_type == 'integer' else json.dumps(value)
        else:
            str_value = str(value)
        
        if setting:
            setting.setting_value = str_value
            setting.setting_type = setting_type
            if description:
                setting.description = description
            setting.updated_at = datetime.utcnow()
        else:
            setting = ChatSettings(
                setting_name=name,
                setting_value=str_value,
                setting_type=setting_type,
                description=description or f'Chat widget setting: {name}'
            )
            db.session.add(setting)
        
        db.session.commit()
        return setting

class SystemPrompt(db.Model):
    """Model for storing system prompts"""
    __tablename__ = 'system_prompts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=False)  # Only one can be active at a time
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemPrompt {self.name}>'
    
    @classmethod
    def get_active_prompt(cls):
        """Get the currently active system prompt text"""
        active_prompt = cls.query.filter_by(is_active=True).first()
        if active_prompt:
            return active_prompt.prompt_text
        
        # Return default comprehensive system prompt if none is active
        return """You are a helpful, knowledgeable AI assistant designed to provide excellent customer support and assistance. You have access to both a knowledge base and API tools to help users.

CORE PRINCIPLES:
- Be friendly, professional, and helpful
- Provide accurate information based on your knowledge base
- Use clear, simple language that users can easily understand
- Be patient and thorough in your explanations
- Always aim to solve the user's problem completely

KNOWLEDGE BASE USAGE:
- Use your knowledge base to answer questions about procedures, instructions, and general information
- Provide step-by-step guidance when users ask "how to" do something
- Explain platform features, capabilities, and limits
- Share best practices and tips

API TOOL USAGE (Conservative):
Only use API tools when users are asking for their CURRENT personal data with direct requests like:
- "give me my [data]" / "show me my [data]" / "what is my [data]"
- "how much [data] do I have" / "how many [data] do I have"

NEVER use API tools for:
- Instructions ("how to", "how do I", "where do I", "what steps")
- General information about the platform
- Capabilities or limits ("how many can I", "what can I do")
- Procedures or processes

RESPONSE STYLE:
- Keep responses conversational and engaging
- Use bullet points or numbered lists for complex information
- Provide examples when helpful
- If you don't know something, say so honestly
- Always end with asking if the user needs any clarification or has other questions

Remember: Your goal is to provide the best possible user experience by being helpful, accurate, and efficient."""
    
    @classmethod
    def set_active_prompt(cls, prompt_id):
        """Set a prompt as active (deactivate all others first)"""
        # Deactivate all prompts
        cls.query.update({cls.is_active: False})
        # Activate the selected one
        selected_prompt = cls.query.get(prompt_id)
        if selected_prompt:
            selected_prompt.is_active = True
            db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'prompt_text': self.prompt_text,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class RagFeedback(db.Model):
    """Model for storing user feedback on RAG responses for training purposes"""
    __tablename__ = 'rag_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    
    # Question and Response Data
    user_question = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    response_type = db.Column(db.String(50), nullable=False)  # 'rag', 'rag_with_memory', etc.
    
    # Feedback Data
    feedback_type = db.Column(db.String(20), nullable=False)  # 'thumbs_up', 'thumbs_down'
    feedback_comment = db.Column(db.Text, nullable=True)  # Optional user comment
    
    # Metadata for Training
    retrieved_chunks = db.Column(db.Text, nullable=True)  # JSON string of retrieved document chunks
    confidence_score = db.Column(db.Float, nullable=True)  # If available from RAG system
    
    # Timestamps
    question_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    feedback_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Training Status
    used_for_training = db.Column(db.Boolean, default=False)
    training_notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<RagFeedback {self.id}: {self.feedback_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'user_question': self.user_question,
            'bot_response': self.bot_response,
            'response_type': self.response_type,
            'feedback_type': self.feedback_type,
            'feedback_comment': self.feedback_comment,
            'retrieved_chunks': self.retrieved_chunks,
            'confidence_score': self.confidence_score,
            'question_timestamp': self.question_timestamp.isoformat() if self.question_timestamp else None,
            'feedback_timestamp': self.feedback_timestamp.isoformat() if self.feedback_timestamp else None,
            'used_for_training': self.used_for_training,
            'training_notes': self.training_notes
        }


class ApiRule(db.Model):
    """Model for storing API routing rules - Legacy (kept for backward compatibility)"""
    __tablename__ = 'api_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    keywords = db.Column(db.Text, nullable=False)  # Comma-separated keywords
    curl_command = db.Column(db.Text, nullable=False)  # Full curl command
    priority = db.Column(db.Integer, default=0)  # Higher priority = checked first
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiRule {self.name}>'
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        return [keyword.strip().lower() for keyword in self.keywords.split(',') if keyword.strip()]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'keywords': self.keywords,
            'curl_command': self.curl_command,
            'priority': self.priority,
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ApiTool(db.Model):
    """Model for storing AI-driven API tools with OpenAI Function Calling support"""
    __tablename__ = 'api_tools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)  # Function name for OpenAI
    description = db.Column(db.Text, nullable=False)  # Description for AI to understand when to use
    parameters = db.Column(db.Text, nullable=False)  # JSON schema for function parameters
    curl_command = db.Column(db.Text, nullable=False)  # Full curl command with placeholders
    response_mapping = db.Column(db.Text, nullable=True)  # JSON mapping for response fields
    response_template = db.Column(db.Text, nullable=True)  # Template for AI response formatting
    priority = db.Column(db.Integer, default=0)  # Higher priority = preferred tool
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiTool {self.name}>'
    
    def get_parameters_schema(self):
        """Return parameters as JSON schema"""
        try:
            return json.loads(self.parameters) if self.parameters else {}
        except json.JSONDecodeError:
            return {}
    
    def get_response_mapping(self):
        """Return response mapping configuration"""
        try:
            return json.loads(self.response_mapping) if self.response_mapping else {}
        except json.JSONDecodeError:
            return {}
    
    def get_openai_function_spec(self):
        """Return OpenAI function specification"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema()
        }
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'curl_command': self.curl_command,
            'response_mapping': self.response_mapping,
            'response_template': self.response_template,
            'priority': self.priority,
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }