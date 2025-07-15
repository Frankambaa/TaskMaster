"""
Session-based memory management for LangChain chatbot.
Each user session gets isolated conversation memory.
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


class SessionChatMessageHistory(BaseChatMessageHistory):
    """In-memory chat message history for a session."""
    
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
    """Manages conversation memory for multiple user sessions."""
    
    def __init__(self, max_token_limit: int = 2000):
        self.max_token_limit = max_token_limit
        self.sessions: Dict[str, SessionChatMessageHistory] = {}
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
    
    def get_or_create_session(self, session_id: str) -> SessionChatMessageHistory:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionChatMessageHistory(session_id)
            # Create memory store for this session
            self.memory_stores[session_id] = ConversationBufferWindowMemory(
                chat_memory=self.sessions[session_id],
                k=10,  # Keep last 10 exchanges
                return_messages=True
            )
        return self.sessions[session_id]
    
    def add_user_message(self, session_id: str, message: str) -> None:
        """Add user message to session history."""
        session = self.get_or_create_session(session_id)
        session.add_message(HumanMessage(content=message))
    
    def add_ai_message(self, session_id: str, message: str) -> None:
        """Add AI message to session history."""
        session = self.get_or_create_session(session_id)
        session.add_message(AIMessage(content=message))
    
    def get_session_history(self, session_id: str) -> List[BaseMessage]:
        """Get conversation history for a session."""
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id].messages
    
    def get_memory_context(self, session_id: str) -> str:
        """Get formatted conversation context for RAG."""
        if session_id not in self.memory_stores:
            return ""
        
        memory = self.memory_stores[session_id]
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
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
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
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about a session."""
        if session_id not in self.sessions:
            return {"exists": False}
        
        messages = self.sessions[session_id].messages
        user_messages = sum(1 for msg in messages if isinstance(msg, HumanMessage))
        ai_messages = sum(1 for msg in messages if isinstance(msg, AIMessage))
        
        return {
            "exists": True,
            "total_messages": len(messages),
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "last_message_type": type(messages[-1]).__name__ if messages else None
        }


# Global session manager instance
session_manager = SessionMemoryManager()