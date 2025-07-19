"""
ElevenLabs Voice Agent Integration
Handles voice-to-voice conversation using ElevenLabs API
Maps to the same RAG and AI tool systems as the main chatbot
"""

import os
import json
import requests
import tempfile
from flask import request, jsonify
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElevenLabsVoiceAgent:
    def __init__(self):
        # ElevenLabs API configuration
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice (English)
        self.model_id = "eleven_multilingual_v2"  # High quality model
        self.api_base = "https://api.elevenlabs.io/v1"
        
        # Voice settings for Indian English accent
        self.voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True
        }
        
        logger.info(f"ElevenLabs Voice Agent initialized with voice_id: {self.voice_id}")

    def synthesize_speech(self, text):
        """
        Convert text to speech using ElevenLabs API
        Returns audio data in bytes format
        """
        if not self.api_key:
            logger.error("ElevenLabs API key not found")
            return None
            
        try:
            url = f"{self.api_base}/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": self.voice_settings
            }
            
            logger.info(f"Synthesizing speech for text: {text[:50]}...")
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                logger.info("Speech synthesis successful")
                return response.content
            else:
                logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {str(e)}")
            return None

    def transcribe_speech(self, audio_data):
        """
        Transcribe speech to text using Web Speech API (browser-side)
        This is a placeholder - actual transcription happens in the browser
        """
        # Note: Speech recognition is handled by the browser's Web Speech API
        # This method is kept for potential future server-side transcription
        logger.info("Speech transcription handled by browser Web Speech API")
        return None

    def process_voice_conversation(self, text_message, user_data=None):
        """
        Process a voice conversation turn:
        1. Take transcribed text from browser
        2. Process through RAG/AI tools (same as main chatbot)
        3. Convert response to speech
        4. Return audio data
        """
        try:
            # Import the main RAG chain for processing
            from rag_chain import process_question
            
            logger.info(f"Processing voice conversation for: {text_message[:50]}...")
            
            # Process through the same RAG/AI system as main chatbot
            response_text = process_question(
                question=text_message,
                session_id=user_data.get('session_id') if user_data else None,
                user_id=user_data.get('user_id') if user_data else None,
                username=user_data.get('username') if user_data else None,
                email=user_data.get('email') if user_data else None,
                device_id=user_data.get('device_id') if user_data else None
            )
            
            logger.info(f"Generated response: {response_text[:50]}...")
            
            # Convert response to speech
            audio_data = self.synthesize_speech(response_text)
            
            if audio_data:
                return {
                    'success': True,
                    'response_text': response_text,
                    'audio_data': audio_data,
                    'audio_format': 'mp3'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to synthesize speech',
                    'response_text': response_text
                }
                
        except Exception as e:
            logger.error(f"Error in voice conversation processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
elevenlabs_agent = ElevenLabsVoiceAgent()

def handle_elevenlabs_voice_request():
    """
    Flask route handler for ElevenLabs voice requests
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        message = data['message']
        user_data = {
            'session_id': data.get('session_id'),
            'user_id': data.get('user_id'),
            'username': data.get('username'),
            'email': data.get('email'),
            'device_id': data.get('device_id')
        }
        
        # Process the voice conversation
        result = elevenlabs_agent.process_voice_conversation(message, user_data)
        
        if result['success']:
            # Return audio as base64 for easy transfer
            import base64
            audio_b64 = base64.b64encode(result['audio_data']).decode('utf-8')
            
            return jsonify({
                'success': True,
                'response': result['response_text'],
                'audio': audio_b64,
                'audio_format': result['audio_format']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'response': result.get('response_text', '')
            }), 500
            
    except Exception as e:
        logger.error(f"Error handling ElevenLabs voice request: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_available_voices():
    """
    Get available ElevenLabs voices
    """
    try:
        if not elevenlabs_agent.api_key:
            return jsonify({
                'success': False,
                'error': 'ElevenLabs API key not configured'
            }), 400
            
        url = f"{elevenlabs_agent.api_base}/voices"
        headers = {"xi-api-key": elevenlabs_agent.api_key}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            voices = response.json()
            return jsonify({
                'success': True,
                'voices': voices['voices']
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500