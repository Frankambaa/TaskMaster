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
    
    def get_session_messages(self, session_id: str, limit: int = 50) -> List[LiveChatMessage]:
        """Get messages for a live chat session"""
        return LiveChatMessage.query.filter_by(session_id=session_id)\
            .order_by(LiveChatMessage.created_at.desc())\
            .limit(limit).all()
    
    def get_agent_sessions(self, agent_id: str, status: str = None) -> List[LiveChatSession]:
        """Get sessions assigned to an agent"""
        query = LiveChatSession.query.filter_by(agent_id=agent_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(LiveChatSession.updated_at.desc()).all()
    
    def get_waiting_sessions(self, department: str = None) -> List[LiveChatSession]:
        """Get sessions waiting for agent assignment"""
        query = LiveChatSession.query.filter_by(status='waiting')
        if department:
            query = query.filter_by(department=department)
        return query.order_by(LiveChatSession.created_at.asc()).all()
    
    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent availability status"""
        agent = LiveChatAgent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return False
        
        agent.status = status
        agent.last_activity = datetime.utcnow()
        db.session.commit()
        
        self.logger.info(f"Updated agent {agent_id} status to {status}")
        return True
    
    def _find_best_agent(self, department: str = None, priority: str = 'normal') -> Optional[LiveChatAgent]:
        """Find the best available agent for assignment"""
        query = LiveChatAgent.query.filter_by(status='online', is_active=True)\
            .filter(LiveChatAgent.current_chat_count < LiveChatAgent.max_concurrent_chats)
        
        if department:
            query = query.filter_by(department=department)
        
        # Order by current chat count (load balancing)
        agents = query.order_by(LiveChatAgent.current_chat_count.asc()).all()
        
        # Filter by skills if needed for high priority requests
        if priority in ['high', 'urgent'] and agents:
            skilled_agents = [agent for agent in agents if 'escalation' in agent.get_skills()]
            if skilled_agents:
                return skilled_agents[0]
        
        return agents[0] if agents else None
    
    def _calculate_session_duration(self, session: LiveChatSession) -> int:
        """Calculate session duration in minutes"""
        if not session.completed_at:
            return 0
        duration = session.completed_at - session.created_at
        return int(duration.total_seconds() / 60)
    
    def _send_webhook_notification(self, event_type: str, payload: Dict[str, Any]):
        """Send webhook notification for live chat events"""
        try:
            webhook_manager.send_to_all_webhooks(event_type, payload)
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {str(e)}")
    
    def get_session_statistics(self, agent_id: str = None, 
                             start_date: datetime = None, 
                             end_date: datetime = None) -> Dict[str, Any]:
        """Get live chat session statistics"""
        query = LiveChatSession.query
        
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        
        if start_date:
            query = query.filter(LiveChatSession.created_at >= start_date)
        
        if end_date:
            query = query.filter(LiveChatSession.created_at <= end_date)
        
        sessions = query.all()
        
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == 'completed'])
        active_sessions = len([s for s in sessions if s.status == 'active'])
        waiting_sessions = len([s for s in sessions if s.status == 'waiting'])
        
        avg_duration = 0
        if completed_sessions > 0:
            total_duration = sum(self._calculate_session_duration(s) for s in sessions if s.completed_at)
            avg_duration = total_duration / completed_sessions
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'active_sessions': active_sessions,
            'waiting_sessions': waiting_sessions,
            'completion_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            'average_duration_minutes': round(avg_duration, 2)
        }

# Global live chat manager instance
live_chat_manager = LiveChatManager()