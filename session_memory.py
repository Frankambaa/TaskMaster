"""
Session-based memory management for LangChain chatbot with persistent user storage.
Each user session gets isolated conversation memory with database persistence.
"""

import os
import uuid
from typing import Dict, List, Any, Optional
from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from models import UserConversation, db


class PersistentChatMessageHistory(BaseChatMessageHistory):
    """Persistent chat message history for a user with database storage."""
    
    def __init__(self, user_identifier: str, username: str = None, email: str = None, device_id: str = None):
        self.user_identifier = user_identifier
        self.username = username
        self.email = email
        self.device_id = device_id
        self.messages: List[BaseMessage] = []
        self._load_from_database()
    
    def _load_from_database(self) -> None:
        """Load conversation history from database."""
        try:
            user_conversation = UserConversation.query.filter_by(user_identifier=self.user_identifier).first()
            if user_conversation:
                history = user_conversation.get_conversation_history()
                self.messages = []
                for msg in history:
                    if msg['type'] == 'human':
                        self.messages.append(HumanMessage(content=msg['content']))
                    elif msg['type'] == 'ai':
                        self.messages.append(AIMessage(content=msg['content']))
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            self.messages = []
    
    def _save_to_database(self) -> None:
        """Save conversation history to database."""
        try:
            user_conversation = UserConversation.query.filter_by(user_identifier=self.user_identifier).first()
            if not user_conversation:
                user_conversation = UserConversation(
                    user_identifier=self.user_identifier,
                    username=self.username,
                    email=self.email,
                    device_id=self.device_id,
                    conversation_data='[]'
                )
                db.session.add(user_conversation)
            
            # Convert messages to serializable format
            history = []
            for msg in self.messages:
                if isinstance(msg, HumanMessage):
                    history.append({'type': 'human', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({'type': 'ai', 'content': msg.content})
            
            user_conversation.set_conversation_history(history)
            # Update user info if provided
            if self.username:
                user_conversation.username = self.username
            if self.email:
                user_conversation.email = self.email
            if self.device_id:
                user_conversation.device_id = self.device_id
            
            db.session.commit()
        except Exception as e:
            print(f"Error saving conversation history: {e}")
            db.session.rollback()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the session history and save to database."""
        self.messages.append(message)
        self._save_to_database()
    
    def clear(self) -> None:
        """Clear all messages from the session and database."""
        self.messages.clear()
        try:
            user_conversation = UserConversation.query.filter_by(user_identifier=self.user_identifier).first()
            if user_conversation:
                user_conversation.clear_conversation()
                db.session.commit()
        except Exception as e:
            print(f"Error clearing conversation history: {e}")
            db.session.rollback()


class SessionChatMessageHistory(BaseChatMessageHistory):
    """In-memory chat message history for temporary sessions."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[BaseMessage] = []
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the session history."""
        self.messages.append(message)
    
    def clear(self) -> None:
        """Clear all messages from the session."""
        self.messages.clear()


class SessionMemoryManager:
    """Manages conversation memory for multiple user sessions with persistent storage."""
    
    def __init__(self, max_token_limit: int = 2000):
        self.max_token_limit = max_token_limit
        self.sessions: Dict[str, SessionChatMessageHistory] = {}  # Temporary sessions
        self.user_sessions: Dict[str, PersistentChatMessageHistory] = {}  # Persistent user sessions
        self.memory_stores: Dict[str, ConversationBufferWindowMemory] = {}
        
        # Initialize OpenAI client
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        self.llm = ChatOpenAI(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            temperature=0.7,
            api_key=self.openai_api_key
        )
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
    
    def get_or_create_user_session(self, user_identifier: str, username: str = None, email: str = None, device_id: str = None) -> PersistentChatMessageHistory:
        """Get existing user session or create new one with persistent storage."""
        if user_identifier not in self.user_sessions:
            self.user_sessions[user_identifier] = PersistentChatMessageHistory(
                user_identifier=user_identifier,
                username=username,
                email=email,
                device_id=device_id
            )
            # Create memory store for this user session
            self.memory_stores[user_identifier] = ConversationBufferWindowMemory(
                chat_memory=self.user_sessions[user_identifier],
                k=10,  # Keep last 10 exchanges
                return_messages=True
            )
        return self.user_sessions[user_identifier]
    
    def get_or_create_session(self, session_id: str) -> SessionChatMessageHistory:
        """Get existing temporary session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionChatMessageHistory(session_id)
            # Create memory store for this session
            self.memory_stores[session_id] = ConversationBufferWindowMemory(
                chat_memory=self.sessions[session_id],
                k=10,  # Keep last 10 exchanges
                return_messages=True
            )
        return self.sessions[session_id]
    
    def add_user_message(self, session_id: str, message: str, user_identifier: str = None, username: str = None, email: str = None, device_id: str = None) -> None:
        """Add user message to session history (persistent or temporary)."""
        if user_identifier:
            session = self.get_or_create_user_session(user_identifier, username, email, device_id)
        else:
            session = self.get_or_create_session(session_id)
        session.add_message(HumanMessage(content=message))
    
    def add_ai_message(self, session_id: str, message: str, user_identifier: str = None, username: str = None, email: str = None, device_id: str = None) -> None:
        """Add AI message to session history (persistent or temporary)."""
        if user_identifier:
            session = self.get_or_create_user_session(user_identifier, username, email, device_id)
        else:
            session = self.get_or_create_session(session_id)
        session.add_message(AIMessage(content=message))
    
    def get_session_history(self, session_id: str, user_identifier: str = None) -> List[BaseMessage]:
        """Get conversation history for a session (persistent or temporary)."""
        if user_identifier:
            if user_identifier not in self.user_sessions:
                return []
            return self.user_sessions[user_identifier].messages
        else:
            if session_id not in self.sessions:
                return []
            return self.sessions[session_id].messages
    
    def get_memory_context(self, session_id: str, user_identifier: str = None) -> str:
        """Get formatted conversation context for RAG."""
        identifier = user_identifier or session_id
        if identifier not in self.memory_stores:
            return ""
        
        memory = self.memory_stores[identifier]
        messages = memory.chat_memory.messages
        
        if not messages:
            return ""
        
        # Format recent conversation for context
        context_parts = []
        for msg in messages[-6:]:  # Last 6 messages (3 exchanges)
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                context_parts.append(f"Assistant: {msg.content}")
        
        return "\n".join(context_parts)
    
    def clear_session(self, session_id: str, user_identifier: str = None) -> None:
        """Clear conversation history for a session (persistent or temporary)."""
        if user_identifier:
            if user_identifier in self.user_sessions:
                self.user_sessions[user_identifier].clear()
            if user_identifier in self.memory_stores:
                self.memory_stores[user_identifier].clear()
        else:
            if session_id in self.sessions:
                self.sessions[session_id].clear()
            if session_id in self.memory_stores:
                self.memory_stores[session_id].clear()
    
    def cleanup_old_sessions(self, max_sessions: int = 100) -> None:
        """Clean up old sessions if too many exist."""
        if len(self.sessions) > max_sessions:
            # Remove oldest sessions (simple cleanup)
            sessions_to_remove = list(self.sessions.keys())[:-max_sessions]
            for session_id in sessions_to_remove:
                self.sessions.pop(session_id, None)
                self.memory_stores.pop(session_id, None)
    
    def get_session_stats(self, session_id: str, user_identifier: str = None) -> Dict[str, Any]:
        """Get statistics about a session (persistent or temporary)."""
        if user_identifier:
            if user_identifier not in self.user_sessions:
                return {"exists": False, "type": "user", "persistent": True}
            messages = self.user_sessions[user_identifier].messages
            session_type = "user"
        else:
            if session_id not in self.sessions:
                return {"exists": False, "type": "temporary", "persistent": False}
            messages = self.sessions[session_id].messages
            session_type = "temporary"
        
        user_messages = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        ai_messages = sum(1 for msg in messages if isinstance(msg, AIMessage))
        
        return {
            "exists": True,
            "type": session_type,
            "persistent": user_identifier is not None,
            "total_messages": len(messages),
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "last_message_type": type(messages[-1]).__name__ if messages else None
        }
    
    def get_user_conversation_info(self, user_identifier: str) -> Optional[Dict[str, Any]]:
        """Get information about a user's conversation from database."""
        try:
            user_conversation = UserConversation.query.filter_by(user_identifier=user_identifier).first()
            if user_conversation:
                return user_conversation.to_dict()
            return None
        except Exception as e:
            print(f"Error getting user conversation info: {e}")
            return None
    
    def get_memory_for_session(self, session_id: str, user_identifier: str = None) -> ConversationBufferWindowMemory:
        """Get memory object for a session (for use with LangChain)."""
        identifier = user_identifier or session_id
        if identifier not in self.memory_stores:
            if user_identifier:
                self.get_or_create_user_session(user_identifier)
            else:
                self.get_or_create_session(session_id)
        return self.memory_stores[identifier]


# Global session manager instance
session_manager = SessionMemoryManager()