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