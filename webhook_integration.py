"""
Webhook Integration System for Third-Party Chat Platforms
Handles incoming messages from external systems and sends responses back
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import current_app
from models import db, WebhookConfig, WebhookMessage, LiveChatSession
import uuid

logger = logging.getLogger(__name__)

class WebhookIntegration:
    def __init__(self):
        self.config = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TaskMaster-RAG-Chatbot/1.0'
        })

    def load_config(self) -> Optional[WebhookConfig]:
        """Load active webhook configuration"""
        try:
            self.config = WebhookConfig.query.filter_by(is_active=True).first()
            return self.config
        except Exception as e:
            logger.error(f"Error loading webhook config: {e}")
            return None

    def process_incoming_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming message from third-party webhook
        Expected format:
        {
            "user_id": "external_user_123",
            "username": "John Doe",
            "message": "Hello, I need help",
            "platform": "freshchat",
            "conversation_id": "conv_456",
            "timestamp": "2025-01-19T12:00:00Z",
            "metadata": {}
        }
        """
        try:
            # Validate required fields
            required_fields = ['user_id', 'message', 'platform']
            missing_fields = [field for field in required_fields if field not in webhook_data]
            if missing_fields:
                return {
                    'success': False,
                    'error': f'Missing required fields: {missing_fields}'
                }

            # Extract message data
            external_user_id = webhook_data['user_id']
            username = webhook_data.get('username', f'User_{external_user_id}')
            message = webhook_data['message']
            platform = webhook_data['platform']
            conversation_id = webhook_data.get('conversation_id', str(uuid.uuid4()))
            
            # Store incoming webhook message
            webhook_msg = WebhookMessage(
                external_user_id=external_user_id,
                external_conversation_id=conversation_id,
                platform=platform,
                message_type='incoming',
                message_content=message,
                username=username,
                message_metadata=json.dumps(webhook_data.get('metadata', {})),
                status='received'
            )
            db.session.add(webhook_msg)
            
            # Process message through chatbot
            response = self.send_to_chatbot(
                message=message,
                user_id=external_user_id,
                username=username,
                platform=platform,
                conversation_id=conversation_id
            )
            
            # Store outgoing response
            response_msg = WebhookMessage(
                external_user_id=external_user_id,
                external_conversation_id=conversation_id,
                platform=platform,
                message_type='outgoing',
                message_content=response.get('answer', 'Sorry, I could not process your request.'),
                username='AI Assistant',
                message_metadata=json.dumps(response),
                status='pending'
            )
            db.session.add(response_msg)
            
            # Send response back to third party if webhook URL is configured
            if self.config and self.config.outgoing_webhook_url:
                webhook_response = self.send_response_to_webhook(
                    response=response,
                    original_data=webhook_data,
                    response_message_id=response_msg.id
                )
                
                if webhook_response['success']:
                    response_msg.status = 'sent'
                else:
                    response_msg.status = 'failed'
                    response_msg.error_message = webhook_response.get('error')
            
            db.session.commit()
            
            return {
                'success': True,
                'response': response,
                'message_id': webhook_msg.id,
                'response_id': response_msg.id
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook message: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def send_to_chatbot(self, message: str, user_id: str, username: str, 
                       platform: str, conversation_id: str) -> Dict[str, Any]:
        """Send message to internal chatbot system and get response"""
        try:
            from rag_chain import process_question_with_memory
            
            # Create user identifier for memory system
            webhook_user_id = f"webhook_{platform}_{user_id}"
            
            # Process through RAG system
            response = process_question_with_memory(
                question=message,
                user_id=webhook_user_id,
                username=username,
                email=None,
                device_id=conversation_id
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending to chatbot: {e}")
            return {
                'answer': 'Sorry, I encountered an error processing your message. Please try again.',
                'response_type': 'error',
                'error': str(e)
            }

    def send_response_to_webhook(self, response: Dict[str, Any], 
                               original_data: Dict[str, Any],
                               response_message_id: int) -> Dict[str, Any]:
        """Send chatbot response back to third-party webhook"""
        try:
            if not self.config or not self.config.outgoing_webhook_url:
                return {'success': False, 'error': 'No outgoing webhook URL configured'}
            
            # Prepare webhook payload
            webhook_payload = {
                'user_id': original_data['user_id'],
                'conversation_id': original_data.get('conversation_id'),
                'platform': original_data['platform'],
                'response_message_id': response_message_id,
                'message': response.get('answer', ''),
                'response_type': response.get('response_type', 'unknown'),
                'timestamp': datetime.utcnow().isoformat(),
                'original_message': original_data['message'],
                'metadata': {
                    'user_info': response.get('user_info', {}),
                    'processing_time': response.get('processing_time', 0)
                }
            }
            
            # Add authentication headers if configured
            headers = {'Content-Type': 'application/json'}
            if self.config.auth_token:
                headers['Authorization'] = f'Bearer {self.config.auth_token}'
            if self.config.custom_headers:
                try:
                    custom_headers = json.loads(self.config.custom_headers)
                    headers.update(custom_headers)
                except:
                    logger.warning("Invalid custom headers JSON format")
            
            # Send webhook request
            response_obj = self.session.post(
                self.config.outgoing_webhook_url,
                json=webhook_payload,
                headers=headers,
                timeout=30
            )
            
            if response_obj.status_code == 200:
                logger.info(f"Webhook response sent successfully to {self.config.outgoing_webhook_url}")
                return {
                    'success': True,
                    'status_code': response_obj.status_code,
                    'response': response_obj.text
                }
            else:
                logger.error(f"Webhook failed with status {response_obj.status_code}: {response_obj.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response_obj.status_code}: {response_obj.text}',
                    'status_code': response_obj.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("Webhook request timed out")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in webhook response: {e}")
            return {'success': False, 'error': str(e)}

    def handle_live_chat_transfer(self, user_id: str, platform: str, 
                                conversation_id: str, message: str) -> Dict[str, Any]:
        """Handle transfer to live chat from webhook message"""
        try:
            # Check if live chat session already exists
            external_session_id = f"{platform}_{conversation_id}"
            existing_session = LiveChatSession.query.filter_by(
                external_session_id=external_session_id
            ).first()
            
            if existing_session and existing_session.status == 'active':
                return {
                    'success': True,
                    'session_id': existing_session.session_id,
                    'message': 'Already connected to live agent'
                }
            
            # Create new live chat session
            session = LiveChatSession(
                user_identifier=f"webhook_{platform}_{user_id}",
                platform=platform,
                external_session_id=external_session_id,
                initial_message=message,
                status='waiting',
                priority='normal'
            )
            db.session.add(session)
            db.session.commit()
            
            return {
                'success': True,
                'session_id': session.session_id,
                'message': 'Transferring to live agent. Please wait...'
            }
            
        except Exception as e:
            logger.error(f"Error handling live chat transfer: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def send_agent_message_to_webhook(self, session_id: str, agent_message: str, 
                                    agent_name: str) -> Dict[str, Any]:
        """Send agent message back to third-party platform"""
        try:
            session = LiveChatSession.query.filter_by(session_id=session_id).first()
            if not session or not session.external_session_id:
                return {'success': False, 'error': 'Session not found'}
            
            # Extract platform and conversation ID
            platform_parts = session.external_session_id.split('_', 1)
            if len(platform_parts) != 2:
                return {'success': False, 'error': 'Invalid external session ID format'}
            
            platform, conversation_id = platform_parts
            
            # Store agent message
            webhook_msg = WebhookMessage(
                external_user_id=session.user_identifier.replace(f'webhook_{platform}_', ''),
                external_conversation_id=conversation_id,
                platform=platform,
                message_type='agent_outgoing',
                message_content=agent_message,
                username=agent_name,
                status='pending'
            )
            db.session.add(webhook_msg)
            
            # Send to webhook if configured
            if self.config and self.config.outgoing_webhook_url:
                webhook_payload = {
                    'user_id': session.user_identifier.replace(f'webhook_{platform}_', ''),
                    'conversation_id': conversation_id,
                    'platform': platform,
                    'message': agent_message,
                    'sender': agent_name,
                    'sender_type': 'agent',
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': session_id
                }
                
                headers = {'Content-Type': 'application/json'}
                if self.config.auth_token:
                    headers['Authorization'] = f'Bearer {self.config.auth_token}'
                
                response = self.session.post(
                    self.config.outgoing_webhook_url,
                    json=webhook_payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    webhook_msg.status = 'sent'
                else:
                    webhook_msg.status = 'failed'
                    webhook_msg.error_message = f'HTTP {response.status_code}: {response.text}'
            
            db.session.commit()
            return {'success': True, 'message_id': webhook_msg.id}
            
        except Exception as e:
            logger.error(f"Error sending agent message to webhook: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

# Global webhook integration instance
webhook_integration = WebhookIntegration()