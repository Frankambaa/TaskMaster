"""
ElevenLabs Embedded Voice Agent Integration
Provides real-time voice conversation with minimal latency using ElevenLabs' native voice agent
"""
import os
import json
import requests
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

class ElevenLabsEmbeddedAgent:
    def __init__(self):
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        self.conversation_id = None
        
    def get_signed_url(self, agent_id):
        """Get signed URL for dashboard-created agent"""
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")
            
        headers = {
            "xi-api-key": self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/convai/conversation/get_signed_url?agent_id={agent_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"ElevenLabs signed URL generated for agent: {agent_id}")
                return result
            else:
                logger.error(f"Failed to get signed URL: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get signed URL: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting signed URL: {e}")
            raise Exception(f"Network error: {e}")
    
    def create_agent_programmatically(self, name, system_prompt=None):
        """Create a new agent programmatically (optional - can use dashboard instead)"""
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")
            
        if not system_prompt:
            system_prompt = """You are Ria, a helpful AI assistant for Apna.co job platform. 
            Keep responses concise and conversational for voice interaction. 
            Help users with job-related questions, account queries, and general support.
            Speak naturally as if having a phone conversation."""
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "name": name,
            "platform_settings": {
                "voice_id": self.voice_id,
                "language": "en"
            },
            "workflow": {
                "system_prompt": system_prompt,
                "first_message": "Hello! I'm Ria from Apna. How can I help you today?"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/conversational-ai/agents",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                agent_id = result.get('agent_id')
                logger.info(f"ElevenLabs agent created: {agent_id}")
                return result
            else:
                logger.error(f"Failed to create agent: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create agent: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error creating agent: {e}")
            raise Exception(f"Network error: {e}")
    
    def list_agents(self):
        """List all available agents"""
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")
            
        headers = {
            "xi-api-key": self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/conversational-ai/agents",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("ElevenLabs agents listed successfully")
                return result
            else:
                logger.error(f"Failed to list agents: {response.status_code} - {response.text}")
                raise Exception(f"Failed to list agents: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error listing agents: {e}")
            raise Exception(f"Network error: {e}")
    
    def add_user_message(self, message):
        """Add a user message to the conversation (for fallback processing)"""
        if not self.conversation_id:
            raise Exception("No active conversation")
            
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "message": message,
            "audio_format": "mp3"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/convai/conversations/{self.conversation_id}/message",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content  # Audio response
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                raise Exception(f"Failed to send message: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {e}")
            raise Exception(f"Network error: {e}")
    
    def end_conversation(self):
        """End the current conversation"""
        if not self.conversation_id:
            return
            
        headers = {
            "xi-api-key": self.api_key
        }
        
        try:
            response = requests.delete(
                f"{self.base_url}/convai/conversations/{self.conversation_id}",
                headers=headers,
                timeout=10
            )
            
            logger.info(f"ElevenLabs conversation ended: {self.conversation_id}")
            self.conversation_id = None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error ending conversation: {e}")
            self.conversation_id = None

# Global instance
embedded_agent = ElevenLabsEmbeddedAgent()