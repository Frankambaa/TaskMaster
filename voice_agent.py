"""
Voice Agent Module with Kokoro TTS fallback to gTTS
Provides text-to-speech functionality for the chatbot without affecting existing functionality
"""

import os
import logging
import tempfile
import io
from typing import Optional, Dict, Any
from flask import jsonify

class VoiceAgent:
    def __init__(self):
        self.kokoro_pipeline = None
        self.is_kokoro_initialized = False
        self.voice_name = 'af_heart'  # American English female voice
        self.sample_rate = 24000
        
    def initialize_kokoro(self) -> bool:
        """Initialize the Kokoro TTS pipeline if available"""
        try:
            # Try to import and initialize Kokoro
            from kokoro import KPipeline
            
            # Initialize with American English (can be changed later)
            self.kokoro_pipeline = KPipeline(lang_code='a')
            self.is_kokoro_initialized = True
            logging.info("✅ Kokoro TTS initialized successfully")
            return True
            
        except ImportError as e:
            logging.warning(f"⚠️ Kokoro not available, using gTTS fallback: {e}")
            return False
        except Exception as e:
            logging.warning(f"⚠️ Failed to initialize Kokoro, using gTTS fallback: {e}")
            return False
    
    def initialize_gtts(self) -> bool:
        """Initialize gTTS as fallback"""
        try:
            from gtts import gTTS
            logging.info("✅ gTTS initialized successfully as fallback")
            return True
        except ImportError as e:
            logging.error(f"❌ gTTS not available: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Failed to initialize gTTS: {e}")
            return False
    
    def synthesize_speech(self, text: str, voice: str = None) -> Optional[Dict[str, Any]]:
        """
        Convert text to speech using Kokoro TTS or gTTS fallback
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (default: af_heart for Kokoro, 'en-in' for gTTS)
            
        Returns:
            Dictionary with audio data and metadata or None if failed
        """
        # Clean text for better synthesis
        cleaned_text = self._clean_text(text)
        
        # Try Kokoro first
        if not self.is_kokoro_initialized:
            self.initialize_kokoro()
        
        if self.is_kokoro_initialized:
            return self._synthesize_with_kokoro(cleaned_text, voice)
        else:
            # Fallback to gTTS
            return self._synthesize_with_gtts(cleaned_text, voice)
    
    def _synthesize_with_kokoro(self, text: str, voice: str = None) -> Optional[Dict[str, Any]]:
        """Synthesize speech using Kokoro TTS"""
        try:
            import soundfile as sf
            
            # Use provided voice or default
            selected_voice = voice or self.voice_name
            
            # Generate speech
            generator = self.kokoro_pipeline(text, voice=selected_voice)
            
            # Get the first (and typically only) output
            for i, (generated_text, phonemes, audio) in enumerate(generator):
                # Create temporary file for audio
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.wav',
                    dir=tempfile.gettempdir()
                )
                
                # Save audio to temporary file
                sf.write(temp_file.name, audio, self.sample_rate)
                
                return {
                    'success': True,
                    'audio_file': temp_file.name,
                    'generated_text': generated_text,
                    'voice_used': selected_voice,
                    'sample_rate': self.sample_rate,
                    'duration': len(audio) / self.sample_rate,
                    'engine': 'kokoro'
                }
                
        except Exception as e:
            logging.error(f"❌ Kokoro speech synthesis failed: {e}")
            return None
    
    def _synthesize_with_gtts(self, text: str, voice: str = None) -> Optional[Dict[str, Any]]:
        """Synthesize speech using Google Text-to-Speech as fallback"""
        try:
            from gtts import gTTS
            
            # Map voice names to gTTS language codes
            voice_mapping = {
                'af_heart': 'en',     # American Female -> English
                'af_sky': 'en',       # American Female -> English
                'am_adam': 'en',      # American Male -> English
                'am_michael': 'en',   # American Male -> English
                'indian_female': 'en-in'  # Indian English female
            }
            
            # Use provided voice or default to Indian English for natural Indian accent
            selected_voice = voice or 'indian_female'
            lang_code = voice_mapping.get(selected_voice, 'en-in')
            
            # Create gTTS object
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Create temporary file for audio
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.mp3',
                dir=tempfile.gettempdir()
            )
            
            # Save audio to temporary file
            tts.save(temp_file.name)
            
            return {
                'success': True,
                'audio_file': temp_file.name,
                'generated_text': text,
                'voice_used': f'gTTS_{lang_code}',
                'sample_rate': 22050,  # Standard gTTS rate
                'duration': len(text) * 0.1,  # Rough estimation
                'engine': 'gtts'
            }
                
        except Exception as e:
            logging.error(f"❌ gTTS speech synthesis failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better TTS synthesis"""
        # Remove markdown formatting
        import re
        
        # Remove markdown bold/italic
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Replace URLs with "link"
        text = re.sub(r'http[s]?://\S+', 'link', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        # Limit length for better synthesis (Kokoro works best with shorter texts)
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text.strip()
    
    def get_available_voices(self) -> list:
        """Get list of available voices from both Kokoro and gTTS"""
        voices = []
        
        # Check which TTS engines are available
        if self.is_kokoro_initialized or self.initialize_kokoro():
            # Kokoro voices (premium quality)
            voices.extend([
                {'id': 'af_heart', 'name': 'American Female (Heart)', 'language': 'en-US', 'gender': 'female', 'engine': 'kokoro'},
                {'id': 'af_sky', 'name': 'American Female (Sky)', 'language': 'en-US', 'gender': 'female', 'engine': 'kokoro'},
                {'id': 'am_adam', 'name': 'American Male (Adam)', 'language': 'en-US', 'gender': 'male', 'engine': 'kokoro'},
                {'id': 'am_michael', 'name': 'American Male (Michael)', 'language': 'en-US', 'gender': 'male', 'engine': 'kokoro'},
            ])
        
        # gTTS voices (always available as fallback)
        if self.initialize_gtts():
            voices.extend([
                {'id': 'indian_female', 'name': 'Indian English Female', 'language': 'en-IN', 'gender': 'female', 'engine': 'gtts'},
                {'id': 'english_female', 'name': 'English Female', 'language': 'en', 'gender': 'female', 'engine': 'gtts'},
                {'id': 'american_english', 'name': 'American English', 'language': 'en-US', 'gender': 'neutral', 'engine': 'gtts'},
            ])
        
        return voices
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """Clean up temporary audio file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
        except Exception as e:
            logging.warning(f"Failed to cleanup temp file {file_path}: {e}")
        return False

# Global voice agent instance
voice_agent = VoiceAgent()