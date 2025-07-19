"""
Live Chat Manager
Handles live chat sessions, agent assignments, and real-time messaging
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from models import (
    LiveChatSession, LiveChatMessage, LiveChatAgent, 
    WebhookConfig, db
)
from webhook_manager import webhook_manager

class LiveChatManager:
    """Manages live chat sessions and agent interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_identifier: str, username: str = None, 
                      email: str = None, initial_message: str = None,
                      department: str = None, priority: str = 'normal') -> LiveChatSession:
        """
        Create a new live chat session
        
        Args:
            user_identifier: User's unique identifier
            username: Display name for the user
            email: User's email address
            initial_message: User's first message
            department: Requested department (sales, support, etc.)
            priority: Session priority (low, normal, high, urgent)
            
        Returns:
            LiveChatSession instance
        """
        session_id = f"live_{uuid.uuid4().hex[:12]}"
        
        session = LiveChatSession(
            session_id=session_id,
            user_identifier=user_identifier,
            username=username,
            email=email,
            department=department,
            priority=priority,
            initial_message=initial_message,
            status='waiting'
        )
        
        db.session.add(session)
        db.session.commit()
        
        self.logger.info(f"Created live chat session {session_id} for user {user_identifier}")
        
        # Send webhook notification
        self._send_webhook_notification('session_created', session.to_dict())
        
        # Try to assign an agent
        self.assign_agent(session_id)
        
        return session
    
    def import_bot_conversation(self, session_id: str, conversation_history: List[Dict]) -> None:
        """
        Import conversation history from chatbot to live chat session
        
        Args:
            session_id: Live chat session ID
            conversation_history: List of conversation messages from chatbot
        """
        try:
            for conv in conversation_history:
                # Check if message already exists
                existing = LiveChatMessage.query.filter_by(
                    session_id=session_id,
                    message_content=conv['content'],
                    sender_type=conv['role']
                ).first()
                
                if not existing:
                    message = LiveChatMessage(
                        message_id=f"import_{uuid.uuid4().hex[:8]}",
                        session_id=session_id,
                        sender_type='bot' if conv['role'] == 'assistant' else 'user',
                        sender_id=conv.get('sender_id', 'imported'),
                        sender_name=conv.get('sender_name', 'Bot' if conv['role'] == 'assistant' else 'User'),
                        message_content=conv['content'],
                        message_type='text',
                        created_at=datetime.utcnow() - timedelta(minutes=len(conversation_history))
                    )
                    db.session.add(message)
            
            db.session.commit()
            self.logger.info(f"Imported {len(conversation_history)} messages to session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error importing conversation history: {str(e)}")
            db.session.rollback()

    def send_message(self, session_id: str, sender_type: str, sender_id: str,
                    message_content: str, sender_name: str = None,
                    message_type: str = 'text', metadata: Dict[str, Any] = None) -> LiveChatMessage:
        """
        Send a message in a live chat session
        
        Args:
            session_id: Live chat session ID
            sender_type: 'user', 'agent', 'system', or 'bot'
            sender_id: ID of the sender
            message_content: Message text content
            sender_name: Display name of sender
            message_type: Type of message (text, image, file, etc.)
            metadata: Additional message metadata
            
        Returns:
            LiveChatMessage instance
        """
        session = LiveChatSession.query.filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Live chat session {session_id} not found")
        
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        message = LiveChatMessage(
            session_id=session_id,
            message_id=message_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            message_content=message_content,
            message_type=message_type
        )
        
        if metadata:
            message.set_metadata(metadata)
        
        db.session.add(message)
        
        # Update session status if needed
        if session.status == 'waiting' and sender_type == 'agent':
            session.status = 'active'
        
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        self.logger.info(f"Message sent in session {session_id} by {sender_type} {sender_id}")
        
        # Send webhook notification
        message_data = message.to_dict()
        message_data.update({
            'session_data': session.to_dict()
        })
        self._send_webhook_notification('new_message', message_data)
        
        return message
    
    def assign_agent(self, session_id: str, agent_id: str = None) -> bool:
        """
        Assign an agent to a live chat session
        
        Args:
            session_id: Live chat session ID
            agent_id: Specific agent ID to assign (optional)
            
        Returns:
            bool: True if agent assigned successfully
        """
        session = LiveChatSession.query.filter_by(session_id=session_id).first()
        if not session:
            self.logger.error(f"Session {session_id} not found for agent assignment")
            return False
        
        if agent_id:
            # Assign specific agent
            agent = LiveChatAgent.query.filter_by(agent_id=agent_id).first()
            if not agent or not agent.is_available():
                self.logger.warning(f"Agent {agent_id} not available for assignment")
                return False
        else:
            # Find best available agent
            agent = self._find_best_agent(session.department, session.priority)
            if not agent:
                self.logger.info(f"No available agents for session {session_id}")
                return False
        
        # Assign agent to session
        session.agent_id = agent.agent_id
        session.agent_name = agent.agent_name
        session.status = 'active'
        
        # Update agent's current chat count
        agent.current_chat_count += 1
        agent.last_activity = datetime.utcnow()
        
        db.session.commit()
        
        self.logger.info(f"Assigned agent {agent.agent_id} to session {session_id}")
        
        # Send system message about agent assignment
        self.send_message(
            session_id=session_id,
            sender_type='system',
            sender_id='system',
            message_content=f"Agent {agent.agent_name} has joined the chat",
            message_type='system_notification'
        )
        
        # Send webhook notification
        assignment_data = {
            'session_id': session_id,
            'agent_id': agent.agent_id,
            'agent_name': agent.agent_name,
            'assigned_at': datetime.utcnow().isoformat()
        }
        self._send_webhook_notification('agent_assigned', assignment_data)
        
        return True
    
    def get_session_messages(self, session_id: str) -> List[LiveChatMessage]:
        """
        Get all messages for a live chat session
        
        Args:
            session_id: Live chat session ID
            
        Returns:
            List of LiveChatMessage instances
        """
        try:
            messages = LiveChatMessage.query.filter_by(
                session_id=session_id
            ).order_by(LiveChatMessage.created_at.asc()).all()
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting session messages: {str(e)}")
            return []

    def update_session_status(self, session_id: str, status: str) -> bool:
        """
        Update the status of a live chat session
        
        Args:
            session_id: Live chat session ID
            status: New status ('waiting', 'active', 'closed', 'transferred')
            
        Returns:
            bool: True if update successful
        """
        try:
            session = LiveChatSession.query.filter_by(session_id=session_id).first()
            if not session:
                self.logger.error(f"Session {session_id} not found for status update")
                return False
            
            old_status = session.status
            session.status = status
            session.updated_at = datetime.utcnow()
            
            # If closing session, free up agent
            if status == 'closed' and session.agent_id:
                agent = LiveChatAgent.query.filter_by(agent_id=session.agent_id).first()
                if agent and agent.current_chat_count > 0:
                    agent.current_chat_count -= 1
                    agent.last_activity = datetime.utcnow()
                
                # Send system message about session closure
                self.send_message(
                    session_id=session_id,
                    sender_type='system',
                    sender_id='system',
                    message_content=f"Chat session has been {status}",
                    message_type='system_notification'
                )
            
            db.session.commit()
            
            self.logger.info(f"Session {session_id} status updated from {old_status} to {status}")
            
            # Send webhook notification
            status_data = {
                'session_id': session_id,
                'old_status': old_status,
                'new_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            self._send_webhook_notification('status_changed', status_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating session status: {str(e)}")
            db.session.rollback()
            return False

    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """
        Update agent availability status
        
        Args:
            agent_id: Agent ID
            status: New status ('online', 'busy', 'offline')
            
        Returns:
            bool: True if update successful
        """
        try:
            agent = LiveChatAgent.query.filter_by(agent_id=agent_id).first()
            if not agent:
                # Create agent if doesn't exist
                agent = LiveChatAgent(
                    agent_id=agent_id,
                    agent_name=f"Agent {agent_id}",
                    status=status,
                    is_active=True
                )
                db.session.add(agent)
            else:
                agent.status = status
                agent.last_activity = datetime.utcnow()
                agent.is_active = (status != 'offline')
            
            db.session.commit()
            
            self.logger.info(f"Agent {agent_id} status updated to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating agent status: {str(e)}")
            db.session.rollback()
            return False

    def complete_session(self, session_id: str, agent_id: str = None) -> bool:
        """
        Complete a live chat session
        
        Args:
            session_id: Live chat session ID
            agent_id: ID of agent completing the session
            
        Returns:
            bool: True if session completed successfully
        """
        session = LiveChatSession.query.filter_by(session_id=session_id).first()
        if not session:
            self.logger.error(f"Session {session_id} not found for completion")
            return False
        
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        
        # Update agent's current chat count
        if session.agent_id:
            agent = LiveChatAgent.query.filter_by(agent_id=session.agent_id).first()
            if agent and agent.current_chat_count > 0:
                agent.current_chat_count -= 1
                agent.last_activity = datetime.utcnow()
        
        db.session.commit()
        
        self.logger.info(f"Completed live chat session {session_id}")
        
        # Send webhook notification
        completion_data = {
            'session_id': session_id,
            'completed_by': agent_id or session.agent_id,
            'completed_at': session.completed_at.isoformat(),
            'duration_minutes': self._calculate_session_duration(session)
        }
        self._send_webhook_notification('session_completed', completion_data)
        
        return True
    
    def transfer_session(self, session_id: str, new_agent_id: str, reason: str = None) -> bool:
        """
        Transfer a session to a different agent
        
        Args:
            session_id: Live chat session ID
            new_agent_id: ID of the new agent
            reason: Reason for transfer
            
        Returns:
            bool: True if transfer successful
        """
        session = LiveChatSession.query.filter_by(session_id=session_id).first()
        if not session:
            return False
        
        new_agent = LiveChatAgent.query.filter_by(agent_id=new_agent_id).first()
        if not new_agent or not new_agent.is_available():
            return False
        
        old_agent_id = session.agent_id
        old_agent_name = session.agent_name
        
        # Update old agent's chat count
        if old_agent_id:
            old_agent = LiveChatAgent.query.filter_by(agent_id=old_agent_id).first()
            if old_agent and old_agent.current_chat_count > 0:
                old_agent.current_chat_count -= 1
        
        # Assign new agent
        session.agent_id = new_agent.agent_id
        session.agent_name = new_agent.agent_name
        session.status = 'transferred'
        
        # Update new agent's chat count
        new_agent.current_chat_count += 1
        new_agent.last_activity = datetime.utcnow()
        
        db.session.commit()
        
        # Send system message about transfer
        transfer_message = f"Chat transferred from {old_agent_name} to {new_agent.agent_name}"
        if reason:
            transfer_message += f" - Reason: {reason}"
        
        self.send_message(
            session_id=session_id,
            sender_type='system',
            sender_id='system',
            message_content=transfer_message,
            message_type='system_notification'
        )
        
        self.logger.info(f"Transferred session {session_id} from {old_agent_id} to {new_agent_id}")
        
        return True
    
    def _find_best_agent(self, department: str = None, priority: str = 'normal') -> Optional[LiveChatAgent]:
        """
        Find the best available agent for assignment
        
        Args:
            department: Preferred department
            priority: Session priority
            
        Returns:
            LiveChatAgent instance or None
        """
        query = LiveChatAgent.query.filter_by(is_active=True, status='online')
        
        # Filter by department if specified
        if department:
            query = query.filter_by(department=department)
        
        # Order by current chat count (least busy first)
        agents = query.order_by(LiveChatAgent.current_chat_count.asc()).all()
        
        # Find agent with capacity
        for agent in agents:
            if agent.current_chat_count < agent.max_concurrent_chats:
                return agent
        
        return None
    
    def _calculate_session_duration(self, session: LiveChatSession) -> int:
        """Calculate session duration in minutes"""
        if session.completed_at:
            duration = session.completed_at - session.created_at
        else:
            duration = datetime.utcnow() - session.created_at
        
        return int(duration.total_seconds() / 60)
    
    def _send_webhook_notification(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send webhook notification for live chat events"""
        try:
            active_config = WebhookConfig.query.filter_by(is_active=True).first()
            if not active_config:
                return
            
            if webhook_manager:
                webhook_manager.send_webhook(active_config, event_type, data)
                
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {str(e)}")

# Create global instance
live_chat_manager = LiveChatManager()