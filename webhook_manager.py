"""
Webhook Manager for Live Chat Integration
Handles webhook notifications to third-party chat systems like FreshChat, Zendesk, etc.
"""

import json
import requests
import logging
import hashlib
import hmac
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from models import WebhookConfig, db

class WebhookManager:
    """Manages webhook integrations for third-party chat systems"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_webhook(self, config: WebhookConfig, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Send webhook notification to third-party system
        
        Args:
            config: WebhookConfig instance
            event_type: Type of event (new_message, session_created, etc.)
            payload: Event data to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not config.is_active:
            self.logger.info(f"Webhook {config.name} is inactive, skipping")
            return False
        
        if event_type not in config.get_event_types():
            self.logger.debug(f"Event type {event_type} not configured for webhook {config.name}")
            return False
        
        # Prepare webhook payload
        webhook_payload = self._prepare_payload(config, event_type, payload)
        
        # Prepare headers
        headers = self._prepare_headers(config, webhook_payload)
        
        # Send webhook with retries
        return self._send_with_retries(config, webhook_payload, headers)
    
    def _prepare_payload(self, config: WebhookConfig, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the webhook payload based on provider format"""
        base_payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'rag_chatbot',
            'data': payload
        }
        
        # Customize payload format based on provider
        if config.provider.lower() == 'freshchat':
            return self._format_freshchat_payload(event_type, payload)
        elif config.provider.lower() == 'zendesk':
            return self._format_zendesk_payload(event_type, payload)
        elif config.provider.lower() == 'intercom':
            return self._format_intercom_payload(event_type, payload)
        else:
            # Generic format for custom webhooks
            return base_payload
    
    def _format_freshchat_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for FreshChat webhook"""
        if event_type == 'new_message':
            return {
                'actor': {
                    'actor_type': payload.get('sender_type', 'user'),
                    'actor_id': payload.get('sender_id'),
                    'first_name': payload.get('sender_name', 'User')
                },
                'action': 'message_create',
                'conversation_id': payload.get('session_id'),
                'message': {
                    'message_type': 'normal',
                    'message_parts': [{
                        'text': {
                            'content': payload.get('message_content')
                        }
                    }],
                    'created_time': payload.get('created_at')
                },
                'data': payload
            }
        elif event_type == 'session_created':
            return {
                'actor': {
                    'actor_type': 'user',
                    'actor_id': payload.get('user_identifier'),
                    'first_name': payload.get('username', 'User'),
                    'email': payload.get('email')
                },
                'action': 'conversation_create',
                'conversation_id': payload.get('session_id'),
                'conversation': {
                    'status': 'new',
                    'priority': payload.get('priority', 'normal'),
                    'created_time': payload.get('created_at')
                },
                'data': payload
            }
        else:
            return {'event_type': event_type, 'data': payload}
    
    def _format_zendesk_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Zendesk webhook"""
        if event_type == 'new_message':
            return {
                'type': 'ticket.message',
                'ticket': {
                    'id': payload.get('session_id'),
                    'external_id': payload.get('session_id'),
                    'requester': {
                        'name': payload.get('sender_name', 'User'),
                        'email': payload.get('email', 'user@example.com')
                    },
                    'subject': f"Chat Message - {payload.get('session_id')}",
                    'description': payload.get('message_content'),
                    'status': 'new',
                    'priority': payload.get('priority', 'normal'),
                    'created_at': payload.get('created_at')
                },
                'data': payload
            }
        elif event_type == 'session_created':
            return {
                'type': 'ticket.created',
                'ticket': {
                    'id': payload.get('session_id'),
                    'external_id': payload.get('session_id'),
                    'requester': {
                        'name': payload.get('username', 'User'),
                        'email': payload.get('email', 'user@example.com')
                    },
                    'subject': f"New Chat Session - {payload.get('session_id')}",
                    'description': payload.get('initial_message', 'New chat session started'),
                    'status': 'new',
                    'priority': payload.get('priority', 'normal'),
                    'tags': payload.get('tags', []),
                    'created_at': payload.get('created_at')
                },
                'data': payload
            }
        else:
            return {'type': f'custom.{event_type}', 'data': payload}
    
    def _format_intercom_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Intercom webhook"""
        if event_type == 'new_message':
            return {
                'type': 'notification_event',
                'topic': 'conversation.user.replied',
                'data': {
                    'type': 'notification_event_data',
                    'item': {
                        'type': 'conversation',
                        'id': payload.get('session_id'),
                        'source': {
                            'type': 'conversation',
                            'id': payload.get('session_id'),
                            'delivered_as': 'customer_initiated'
                        },
                        'user': {
                            'id': payload.get('sender_id'),
                            'name': payload.get('sender_name', 'User'),
                            'email': payload.get('email')
                        },
                        'conversation_message': {
                            'type': 'conversation_message',
                            'body': payload.get('message_content'),
                            'delivered_as': 'customer_initiated'
                        }
                    }
                },
                'created_at': int(time.time())
            }
        else:
            return {'type': f'custom_{event_type}', 'data': payload}
    
    def _prepare_headers(self, config: WebhookConfig, payload: Dict[str, Any]) -> Dict[str, str]:
        """Prepare HTTP headers for webhook request"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RAG-Chatbot-Webhook/1.0'
        }
        
        # Add custom headers
        custom_headers = config.get_headers()
        headers.update(custom_headers)
        
        # Add authentication headers
        auth_type = config.auth_type
        auth_creds = config.get_auth_credentials()
        
        if auth_type == 'bearer' and 'token' in auth_creds:
            headers['Authorization'] = f"Bearer {auth_creds['token']}"
        elif auth_type == 'basic' and 'username' in auth_creds and 'password' in auth_creds:
            import base64
            credentials = f"{auth_creds['username']}:{auth_creds['password']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded_credentials}"
        elif auth_type == 'api_key' and 'key' in auth_creds and 'header' in auth_creds:
            headers[auth_creds['header']] = auth_creds['key']
        
        # Add webhook signature if secret is configured
        if config.webhook_secret:
            signature = self._generate_signature(config.webhook_secret, json.dumps(payload))
            headers['X-Webhook-Signature'] = signature
            headers['X-Webhook-Signature-256'] = f"sha256={signature}"
        
        return headers
    
    def _generate_signature(self, secret: str, payload: str) -> str:
        """Generate webhook signature for verification"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _send_with_retries(self, config: WebhookConfig, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Send webhook with retry logic"""
        max_retries = config.retry_count
        timeout = config.timeout_seconds
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Sending webhook to {config.name} (attempt {attempt + 1}/{max_retries + 1})")
                
                response = requests.post(
                    config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    self.logger.info(f"Webhook {config.name} sent successfully: {response.status_code}")
                    
                    # Update last_used timestamp
                    config.last_used = datetime.utcnow()
                    db.session.commit()
                    
                    return True
                else:
                    self.logger.warning(f"Webhook {config.name} failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Webhook {config.name} timed out (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Webhook {config.name} connection error (attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"Webhook {config.name} unexpected error: {str(e)}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s...
                time.sleep(wait_time)
        
        self.logger.error(f"Webhook {config.name} failed after {max_retries + 1} attempts")
        return False
    
    def send_to_all_webhooks(self, event_type: str, payload: Dict[str, Any]) -> List[bool]:
        """
        Send event to all active webhooks that support the event type
        
        Args:
            event_type: Type of event to send
            payload: Event data
            
        Returns:
            List of boolean results for each webhook
        """
        webhooks = WebhookConfig.query.filter_by(is_active=True).all()
        results = []
        
        for webhook in webhooks:
            try:
                result = self.send_webhook(webhook, event_type, payload)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error sending to webhook {webhook.name}: {str(e)}")
                results.append(False)
        
        return results
    
    def test_webhook(self, config: WebhookConfig) -> Dict[str, Any]:
        """
        Test webhook configuration with a sample payload
        
        Args:
            config: WebhookConfig to test
            
        Returns:
            Dictionary with test results
        """
        test_payload = {
            'session_id': 'test_session_123',
            'user_identifier': 'test_user',
            'username': 'Test User',
            'email': 'test@example.com',
            'message_content': 'This is a test message from RAG Chatbot',
            'sender_type': 'user',
            'sender_id': 'test_user',
            'sender_name': 'Test User',
            'created_at': datetime.utcnow().isoformat(),
            'priority': 'normal'
        }
        
        try:
            success = self.send_webhook(config, 'new_message', test_payload)
            return {
                'success': success,
                'message': 'Test webhook sent successfully' if success else 'Test webhook failed',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Test webhook error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }

# Global webhook manager instance
webhook_manager = WebhookManager()