#!/usr/bin/env python3
"""
VoiceGuard Windows Speech Recognition
Windows Speech Recognition API integration for offline processing
"""

import speech_recognition as sr
import threading
import queue
import logging
from typing import Optional, Dict, List
import numpy as np
import difflib


class WindowsSpeechRecognizer:
    """Windows Speech Recognition API integration"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.logger = logging.getLogger("WindowsSpeech")
        
        # Configure recognizer settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = 5.0
        
        # Calibrate for ambient noise
        self.calibrate_microphone()
        
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            with self.microphone as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.logger.info(f"Microphone calibrated. Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            self.logger.error(f"Microphone calibration failed: {e}")
            
    async def recognize_audio(self, audio_data: np.ndarray, sample_rate: int) -> Optional[Dict]:
        """Recognize speech using Windows Speech Recognition"""
        try:
            # Convert numpy array to AudioData
            audio_bytes = audio_data.tobytes()
            audio_source = sr.AudioData(audio_bytes, sample_rate, 2)  # 16-bit samples
            
            # Try multiple recognition engines
            results = []
            
            # Try Windows Speech Recognition (if available)
            try:
                text = self.recognizer.recognize_sphinx(audio_source)
                if text:
                    results.append({
                        'text': text.lower().strip(),
                        'confidence': 0.7,  # Sphinx doesn't provide confidence
                        'source': 'windows_speech',
                        'engine': 'sphinx'
                    })
            except sr.UnknownValueError:
                pass  # No speech detected
            except sr.RequestError as e:
                self.logger.debug(f"Sphinx recognition error: {e}")
                
            # Try Google Speech Recognition (if available and online)
            try:
                text = self.recognizer.recognize_google(audio_source, language='en-US')
                if text:
                    results.append({
                        'text': text.lower().strip(),
                        'confidence': 0.8,
                        'source': 'windows_speech',
                        'engine': 'google'
                    })
            except (sr.UnknownValueError, sr.RequestError):
                pass  # Offline or no speech detected
                
            # Return best result
            if results:
                return max(results, key=lambda x: x['confidence'])
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Windows speech recognition error: {e}")
            return None
            
    async def recognize_with_grammar(self, audio_data: np.ndarray, sample_rate: int, 
                                   commands: List[str]) -> Optional[Dict]:
        """Recognize speech with specific command grammar"""
        try:
            # For Windows Speech Recognition, we'll use keyword matching
            # after basic recognition since grammar support is limited in speech_recognition
            
            result = await self.recognize_audio(audio_data, sample_rate)
            if not result:
                return None
                
            # Check if recognized text matches any commands
            recognized_text = result['text']
            best_match = None
            best_confidence = 0
            
            for command in commands:
                # Simple fuzzy matching
                similarity = self.calculate_similarity(recognized_text, command.lower())
                if similarity > best_confidence and similarity > 0.6:
                    best_confidence = similarity
                    best_match = command
                    
            if best_match:
                result['matched_command'] = best_match
                result['confidence'] = min(result['confidence'] * best_confidence, 1.0)
                return result
                
            return None
            
        except Exception as e:
            self.logger.error(f"Grammar recognition error: {e}")
            return None
            
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_similarity = len(intersection) / len(union)
        
        # Also use sequence matching for better accuracy
        sequence_similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        
        # Weighted average
        return 0.6 * jaccard_similarity + 0.4 * sequence_similarity
        
    def get_available_microphones(self) -> List[Dict]:
        """Get list of available microphone devices"""
        try:
            microphones = []
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                microphones.append({
                    'index': index,
                    'name': name
                })
            return microphones
        except Exception as e:
            self.logger.error(f"Failed to get microphones: {e}")
            return []
            
    def set_microphone_device(self, device_index: int) -> bool:
        """Set the microphone device to use"""
        try:
            self.microphone = sr.Microphone(device_index=device_index)
            self.calibrate_microphone()
            return True
        except Exception as e:
            self.logger.error(f"Failed to set microphone device: {e}")
            return False
            
    def adjust_for_ambient_noise(self, duration: float = 1.0):
        """Adjust recognition sensitivity for ambient noise"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                self.logger.info(f"Adjusted for ambient noise. New threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            self.logger.error(f"Ambient noise adjustment failed: {e}")
            
    def test_microphone(self) -> Dict:
        """Test microphone functionality"""
        try:
            with self.microphone as source:
                self.logger.info("Testing microphone - speak now...")
                
                # Listen for 3 seconds
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                
                # Try to recognize
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return {
                        'success': True,
                        'text': text,
                        'message': 'Microphone test successful'
                    }
                except sr.UnknownValueError:
                    return {
                        'success': True,
                        'text': '',
                        'message': 'Microphone working but no speech detected'
                    }
                except sr.RequestError as e:
                    return {
                        'success': False,
                        'text': '',
                        'message': f'Recognition error: {e}'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'text': '',
                'message': f'Microphone test failed: {e}'
            }
            
    def get_audio_level(self) -> float:
        """Get current audio input level (0.0 to 1.0)"""
        try:
            with self.microphone as source:
                # Listen for a very short time to get audio level
                audio = self.recognizer.listen(source, timeout=0.1, phrase_time_limit=0.1)
                
                # Calculate RMS level
                audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                
                # Normalize to 0-1 range (assuming 16-bit audio)
                normalized_level = min(rms / 32767.0, 1.0)
                
                return normalized_level
                
        except Exception as e:
            self.logger.debug(f"Audio level detection error: {e}")
            return 0.0
            
    def configure_recognition_settings(self, **kwargs):
        """Configure recognition settings"""
        if 'energy_threshold' in kwargs:
            self.recognizer.energy_threshold = kwargs['energy_threshold']
            
        if 'dynamic_energy_threshold' in kwargs:
            self.recognizer.dynamic_energy_threshold = kwargs['dynamic_energy_threshold']
            
        if 'pause_threshold' in kwargs:
            self.recognizer.pause_threshold = kwargs['pause_threshold']
            
        if 'operation_timeout' in kwargs:
            self.recognizer.operation_timeout = kwargs['operation_timeout']
            
        self.logger.info(f"Recognition settings updated: {kwargs}")
        
    def get_recognition_settings(self) -> Dict:
        """Get current recognition settings"""
        return {
            'energy_threshold': self.recognizer.energy_threshold,
            'dynamic_energy_threshold': self.recognizer.dynamic_energy_threshold,
            'pause_threshold': self.recognizer.pause_threshold,
            'operation_timeout': self.recognizer.operation_timeout
        }
