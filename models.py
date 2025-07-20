from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

# Database configuration
db = SQLAlchemy()

class UnifiedConversation(db.Model):
    """Unified model for storing both chatbot and live chat conversations"""
    __tablename__ = 'unified_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # Unique session identifier
    user_identifier = db.Column(db.String(255), nullable=False, index=True)  # user_id, email, or device_id
    username = db.Column(db.String(255), nullable=True)  # Optional username for display
    email = db.Column(db.String(255), nullable=True)  # Optional email
    device_id = db.Column(db.String(255), nullable=True)  # Optional device identifier
    
    # Agent information (for live chat)
    agent_id = db.Column(db.String(255), nullable=True)  # Assigned agent identifier (null for chatbot)
    agent_name = db.Column(db.String(255), nullable=True)  # Agent display name
    
    # Conversation type and status
    conversation_type = db.Column(db.String(50), default='chatbot')  # 'chatbot' or 'live_chat'
    status = db.Column(db.String(50), default='active')  # active, waiting, completed, transferred, closed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    department = db.Column(db.String(100), nullable=True)  # sales, support, technical, etc.
    
    # Metadata
    initial_message = db.Column(db.Text, nullable=True)  # First user message
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    extra_metadata = db.Column(db.Text, nullable=True)  # Additional JSON metadata
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship with messages
    messages = db.relationship('UnifiedMessage', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UnifiedConversation {self.session_id} ({self.conversation_type})>'
    
    def get_tags(self):
        """Return tags as list"""
        try:
            return json.loads(self.tags) if self.tags else []
        except json.JSONDecodeError:
            return []
    
    def set_tags(self, tag_list):
        """Set tags from list"""
        self.tags = json.dumps(tag_list)
    
    def get_metadata(self):
        """Return metadata as dict"""
        try:
            return json.loads(self.extra_metadata) if self.extra_metadata else {}
        except json.JSONDecodeError:
            return {}
    
    def set_metadata(self, meta_dict):
        """Set metadata from dict"""
        self.extra_metadata = json.dumps(meta_dict)
    
    def get_conversation_history(self):
        """Return conversation history as list of messages for compatibility"""
        messages = self.messages.order_by(UnifiedMessage.created_at.asc()).all()
        return [
            {
                'type': 'human' if msg.sender_type == 'user' else 'ai',
                'content': msg.message_content,
                'timestamp': msg.created_at.isoformat(),
                'sender_type': msg.sender_type,
                'sender_name': msg.sender_name
            }
            for msg in messages
        ]
    
    def add_message(self, sender_type, content, sender_id=None, sender_name=None, message_type='text', response_type=None):
        """Add a single message to conversation"""
        from uuid import uuid4
        
        message = UnifiedMessage(
            session_id=self.session_id,
            message_id=f"msg_{uuid4().hex[:12]}",
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            message_content=content,
            message_type=message_type,
            response_type=response_type
        )
        db.session.add(message)
        
        # Update conversation timestamps
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Check for live agent requests in user messages
        if sender_type == 'user' and self.detect_live_agent_request(content):
            self.add_live_agent_tag()
        
        return message
    
    def detect_live_agent_request(self, message_content):
        """Detect if user is requesting to talk with a live agent"""
        if not message_content:
            return False
            
        message_lower = message_content.lower().strip()
        
        # Define patterns for live agent requests
        agent_patterns = [
            'talk with agent', 'talk to agent', 'chat with agent', 'speak with agent',
            'live chat', 'live agent', 'human agent', 'real person', 'customer support',
            'transfer to agent', 'transfer to human', 'connect me to agent',
            'speak to someone', 'talk to someone', 'human support', 'agent please',
            'i need help from agent', 'can i talk to agent', 'could you transfer',
            'transfer me to', 'connect to agent', 'agent help', 'live support',
            'talk to a person', 'speak to a person', 'human help'
        ]
        
        # Check if any pattern matches
        for pattern in agent_patterns:
            if pattern in message_lower:
                return True
                
        return False
    
    def add_live_agent_tag(self):
        """Add Live Agent tag to conversation"""
        current_tags = self.get_tags()
        if 'Live Agent' not in current_tags:
            current_tags.append('Live Agent')
            self.set_tags(current_tags)
            db.session.commit()
            print(f"🏷️ Added 'Live Agent' tag to session {self.session_id}")
    
    def set_live_chat_mode(self):
        """Set conversation to live chat mode (disables RAG)"""
        current_tags = self.get_tags()
        if 'Live Chat' not in current_tags:
            current_tags.append('Live Chat')
            self.set_tags(current_tags)
            self.status = 'live_chat'  # Set special status
            db.session.commit()
            print(f"🔄 Enabled Live Chat mode for session {self.session_id}")
    
    def is_live_chat_active(self):
        """Check if conversation is in live chat mode"""
        return 'Live Chat' in self.get_tags() or self.status == 'live_chat'
    
    @classmethod
    def get_or_create(cls, session_id, user_identifier=None, username=None, email=None, device_id=None):
        """Get existing conversation or create new one"""
        # Try to find existing conversation by session_id
        conversation = cls.query.filter_by(session_id=session_id).first()
        
        if conversation:
            # Update user information if provided and different
            if user_identifier and conversation.user_identifier != user_identifier:
                conversation.user_identifier = user_identifier
            if username and conversation.username != username:
                conversation.username = username
            if email and conversation.email != email:
                conversation.email = email
            if device_id and conversation.device_id != device_id:
                conversation.device_id = device_id
            conversation.last_activity = datetime.utcnow()
            db.session.commit()
        else:
            # Create new conversation
            conversation = cls(
                session_id=session_id,
                user_identifier=user_identifier or session_id,
                username=username,
                email=email,
                device_id=device_id,
                conversation_type='chatbot'
            )
            db.session.add(conversation)
            db.session.commit()
            
        return conversation
    
    def has_live_agent_tag(self):
        """Check if conversation has Live Agent tag"""
        return 'Live Agent' in self.get_tags()
    
    def clear_conversation(self):
        """Clear all conversation messages"""
        self.messages.delete()
        self.last_activity = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization with IST timezone"""
        from datetime import timezone, timedelta
        
        # Convert UTC to IST
        ist_timezone = timezone(timedelta(hours=5, minutes=30))
        
        def convert_to_ist(dt):
            if dt:
                return dt.replace(tzinfo=timezone.utc).astimezone(ist_timezone).strftime('%Y-%m-%d %H:%M:%S IST')
            return None
        
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_identifier': self.user_identifier,
            'username': self.username or 'Anonymous User',
            'email': self.email or 'Not provided',
            'device_id': self.device_id,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'conversation_type': self.conversation_type,
            'status': self.status,
            'priority': self.priority,
            'department': self.department,
            'initial_message': self.initial_message,
            'tags': self.get_tags(),
            'extra_metadata': self.get_metadata(),
            'created_at': convert_to_ist(self.created_at),
            'updated_at': convert_to_ist(self.updated_at),
            'last_activity': convert_to_ist(self.last_activity),
            'completed_at': convert_to_ist(self.completed_at),
            'message_count': self.messages.count()
        }

class UnifiedMessage(db.Model):
    """Unified model for storing individual messages in conversations"""
    __tablename__ = 'unified_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), db.ForeignKey('unified_conversations.session_id'), nullable=False, index=True)
    message_id = db.Column(db.String(255), unique=True, nullable=False)  # Unique message identifier
    sender_type = db.Column(db.String(20), nullable=False)  # user, agent, system, bot, assistant
    sender_id = db.Column(db.String(255), nullable=True)  # Agent ID or user identifier
    sender_name = db.Column(db.String(255), nullable=True)  # Display name
    message_content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')  # text, image, file, system_notification
    response_type = db.Column(db.String(50), nullable=True)  # SMALL_TALK, RAG_KNOWLEDGE_BASE, AI_TOOL, TEMPLATE_MATCH
    message_metadata = db.Column(db.Text, nullable=True)  # JSON metadata (file info, etc.)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UnifiedMessage {self.message_id}>'
    
    def get_metadata(self):
        """Return metadata as dict"""
        try:
            return json.loads(self.message_metadata) if self.message_metadata else {}
        except json.JSONDecodeError:
            return {}
    
    def set_metadata(self, meta_dict):
        """Set metadata from dict"""
        self.message_metadata = json.dumps(meta_dict)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization with IST timezone"""
        from datetime import timezone, timedelta
        
        # Convert UTC to IST
        ist_timezone = timezone(timedelta(hours=5, minutes=30))
        created_at_ist = self.created_at.replace(tzinfo=timezone.utc).astimezone(ist_timezone)
        
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message_id': self.message_id,
            'sender_type': self.sender_type,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'message_content': self.message_content,
            'message_type': self.message_type,
            'response_type': self.response_type,
            'message_metadata': self.get_metadata(),
            'is_read': self.is_read,
            'created_at': created_at_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
            'timestamp': created_at_ist.strftime('%H:%M:%S')
        }

# Legacy alias for backward compatibility
UserConversation = UnifiedConversation

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
    
    # Response Analysis Fields (for training improvements)
    response_category = db.Column(db.String(100), nullable=True)  # 'vague', 'helpful', 'incorrect', 'too_technical', etc.
    improvement_suggestions = db.Column(db.Text, nullable=True)  # Admin suggestions for improvement
    admin_notes = db.Column(db.Text, nullable=True)  # General admin notes
    training_priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'critical'
    
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
            'training_notes': self.training_notes,
            'response_category': self.response_category,
            'improvement_suggestions': self.improvement_suggestions,
            'admin_notes': self.admin_notes,
            'training_priority': self.training_priority
        }


class ResponseTemplate(db.Model):
    """Model for storing improved response templates for training the bot"""
    __tablename__ = 'response_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # Trigger conditions
    trigger_keywords = db.Column(db.JSON, nullable=True)  # Array of keywords that should trigger this template
    question_patterns = db.Column(db.JSON, nullable=True)  # Array of question patterns (regex or plain text)
    categories = db.Column(db.JSON, nullable=True)  # Array of response categories this template addresses
    
    # Template content
    template_text = db.Column(db.Text, nullable=False)  # The improved response template
    fallback_response = db.Column(db.Text, nullable=True)  # Fallback if template fails
    
    # Configuration
    priority = db.Column(db.Integer, default=0)  # Higher priority templates are checked first
    is_active = db.Column(db.Boolean, default=True)
    requires_context = db.Column(db.Boolean, default=False)  # Whether template needs RAG context
    
    # Metadata
    usage_count = db.Column(db.Integer, default=0)  # How many times this template was used
    success_rate = db.Column(db.Float, default=0.0)  # Success rate based on feedback
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255), nullable=True)  # Admin who created this
    
    def __repr__(self):
        return f'<ResponseTemplate {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'trigger_keywords': self.trigger_keywords,
            'question_patterns': self.question_patterns,
            'categories': self.categories,
            'template_text': self.template_text,
            'fallback_response': self.fallback_response,
            'priority': self.priority,
            'is_active': self.is_active,
            'requires_context': self.requires_context,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        db.session.commit()
    
    def update_success_rate(self, is_successful):
        """Update success rate based on feedback"""
        # Simple success rate calculation - can be made more sophisticated
        if self.usage_count > 0:
            current_successes = self.success_rate * self.usage_count
            if is_successful:
                current_successes += 1
            self.success_rate = current_successes / self.usage_count
            db.session.commit()


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

# Legacy aliases for backward compatibility
LiveChatSession = UnifiedConversation
LiveChatMessage = UnifiedMessage

class LiveChatAgent(db.Model):
    """Model for managing live chat agents"""
    __tablename__ = 'live_chat_agents'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(255), unique=True, nullable=False)
    agent_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='offline')  # online, offline, busy, away
    max_concurrent_chats = db.Column(db.Integer, default=5)
    current_chat_count = db.Column(db.Integer, default=0)
    skills = db.Column(db.Text, nullable=True)  # JSON array of skills
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<LiveChatAgent {self.agent_name}>'
    
    def get_skills(self):
        """Return skills as list"""
        try:
            return json.loads(self.skills) if self.skills else []
        except json.JSONDecodeError:
            return []
    
    def set_skills(self, skill_list):
        """Set skills from list"""
        self.skills = json.dumps(skill_list)
    
    def is_available(self):
        """Check if agent is available for new chats"""
        return (self.status == 'online' and 
                self.is_active and 
                self.current_chat_count < self.max_concurrent_chats)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'email': self.email,
            'department': self.department,
            'status': self.status,
            'max_concurrent_chats': self.max_concurrent_chats,
            'current_chat_count': self.current_chat_count,
            'skills': self.get_skills(),
            'last_activity': self.last_activity.isoformat(),
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'is_available': self.is_available()
        }

class WebhookConfig(db.Model):
    """Model for storing webhook configurations for third-party integrations"""
    __tablename__ = 'webhook_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # Display name for the webhook
    provider = db.Column(db.String(100), nullable=False)  # freshchat, zendesk, intercom, etc.
    webhook_url = db.Column(db.Text, nullable=False)  # Target webhook URL
    webhook_secret = db.Column(db.String(255), nullable=True)  # Secret for verification
    event_types = db.Column(db.Text, nullable=False, default='["message"]')  # JSON array of events to send
    headers = db.Column(db.Text, nullable=True)  # JSON object of custom headers
    auth_type = db.Column(db.String(50), default='none')  # none, bearer, basic, api_key
    auth_credentials = db.Column(db.Text, nullable=True)  # JSON object with auth details
    is_active = db.Column(db.Boolean, default=True)
    retry_count = db.Column(db.Integer, default=3)  # Number of retry attempts
    timeout_seconds = db.Column(db.Integer, default=30)  # Request timeout
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<WebhookConfig {self.name}>'
    
    def get_event_types(self):
        """Return event types as list"""
        try:
            return json.loads(self.event_types) if self.event_types else []
        except json.JSONDecodeError:
            return []
    
    def set_event_types(self, event_list):
        """Set event types from list"""
        self.event_types = json.dumps(event_list)
    
    def get_headers(self):
        """Return headers as dict"""
        try:
            return json.loads(self.headers) if self.headers else {}
        except json.JSONDecodeError:
            return {}
    
    def set_headers(self, header_dict):
        """Set headers from dict"""
        self.headers = json.dumps(header_dict)
    
    def get_auth_credentials(self):
        """Return auth credentials as dict"""
        try:
            return json.loads(self.auth_credentials) if self.auth_credentials else {}
        except json.JSONDecodeError:
            return {}
    
    def set_auth_credentials(self, auth_dict):
        """Set auth credentials from dict"""
        self.auth_credentials = json.dumps(auth_dict)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'webhook_url': self.webhook_url,
            'incoming_webhook_url': getattr(self, 'incoming_webhook_url', None),
            'outgoing_webhook_url': getattr(self, 'outgoing_webhook_url', None),
            'event_types': self.get_event_types(),
            'headers': self.get_headers(),
            'auth_type': self.auth_type,
            'auth_token': getattr(self, 'auth_token', None),
            'webhook_secret': getattr(self, 'webhook_secret', None),
            'is_active': self.is_active,
            'retry_count': self.retry_count,
            'timeout_seconds': self.timeout_seconds,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None
        }


class WebhookMessage(db.Model):
    """Messages sent/received through webhook integrations"""
    __tablename__ = 'webhook_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    external_user_id = db.Column(db.String(100), nullable=False)
    external_conversation_id = db.Column(db.String(100))
    platform = db.Column(db.String(50), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # 'incoming', 'outgoing', 'agent_outgoing'
    message_content = db.Column(db.Text, nullable=False)
    username = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'failed', 'received'
    error_message = db.Column(db.Text)
    message_metadata = db.Column(db.Text)  # JSON string for additional data
    retry_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'external_user_id': self.external_user_id,
            'external_conversation_id': self.external_conversation_id,
            'platform': self.platform,
            'message_type': self.message_type,
            'message_content': self.message_content,
            'username': self.username,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }

