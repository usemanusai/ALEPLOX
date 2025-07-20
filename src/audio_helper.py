#!/usr/bin/env python3
"""
VoiceGuard Audio Helper Process
User session process for audio monitoring and AI integration
"""

import asyncio
import pyaudio
import numpy as np
import speech_recognition as sr
import aiohttp
import json
import base64
import hashlib
from datetime import datetime, timezone
import threading
import queue
import logging
from typing import Optional, Dict, List
from pathlib import Path

from ipc_communication import IPCClient, IPCMessage
from openrouter_client import OpenRouterClient
from windows_speech import WindowsSpeechRecognizer
from keyword_matcher import KeywordMatcher
from audio_processor import AudioProcessor
from system_tray import SystemTrayApp


class AudioHelperProcess:
    """User session process for audio monitoring and AI integration"""
    
    def __init__(self):
        self.is_running = False
        self.audio_queue = queue.Queue(maxsize=100)
        self.recognition_queue = queue.Queue(maxsize=50)
        self.ipc_client = IPCClient()
        self.openrouter_client = OpenRouterClient()
        self.windows_speech = WindowsSpeechRecognizer()
        self.keyword_matcher = KeywordMatcher()
        self.audio_processor = AudioProcessor()
        self.system_tray = SystemTrayApp()
        
        # Audio configuration
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.audio_format = pyaudio.paInt16
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for helper process"""
        log_path = Path("C:/ProgramData/VoiceGuard/logs")
        log_path.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / "helper.log"),
                logging.handlers.RotatingFileHandler(
                    log_path / "helper_rotating.log",
                    maxBytes=5*1024*1024,  # 5MB
                    backupCount=3
                )
            ]
        )
        self.logger = logging.getLogger("AudioHelper")
        
    async def start(self):
        """Start the audio helper process"""
        self.logger.info("Starting VoiceGuard Audio Helper...")
        self.is_running = True
        
        try:
            # Initialize components
            await self.ipc_client.connect()
            await self.openrouter_client.initialize()
            self.system_tray.start()
            
            # Start audio processing tasks
            tasks = [
                asyncio.create_task(self.audio_capture_loop()),
                asyncio.create_task(self.audio_processing_loop()),
                asyncio.create_task(self.recognition_loop()),
                asyncio.create_task(self.status_reporting_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"Audio helper error: {e}")
        finally:
            await self.cleanup()
            
    async def audio_capture_loop(self):
        """Continuous audio capture from microphone"""
        audio = pyaudio.PyAudio()
        
        try:
            # Open microphone stream
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_callback
            )
            
            stream.start_stream()
            self.logger.info("Audio capture started")
            
            while self.is_running and stream.is_active():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Audio capture error: {e}")
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            audio.terminate()
            
    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for real-time audio processing"""
        try:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Voice activity detection
            if self.audio_processor.detect_voice_activity(audio_data):
                # Add to processing queue
                if not self.audio_queue.full():
                    self.audio_queue.put({
                        'data': audio_data,
                        'timestamp': datetime.now(timezone.utc),
                        'sample_rate': self.sample_rate
                    })
                    
        except Exception as e:
            self.logger.error(f"Audio callback error: {e}")
            
        return (None, pyaudio.paContinue)
        
    async def audio_processing_loop(self):
        """Process audio chunks for speech recognition"""
        audio_buffer = []
        buffer_duration = 3.0  # 3 seconds
        buffer_size = int(self.sample_rate * buffer_duration)
        
        while self.is_running:
            try:
                # Get audio chunk from queue
                if not self.audio_queue.empty():
                    audio_chunk = self.audio_queue.get_nowait()
                    audio_buffer.extend(audio_chunk['data'])
                    
                    # Process when buffer is full
                    if len(audio_buffer) >= buffer_size:
                        # Create audio segment for recognition
                        audio_segment = np.array(audio_buffer[-buffer_size:], dtype=np.int16)
                        
                        # Enhance audio quality
                        enhanced_audio = self.audio_processor.enhance_audio(audio_segment)
                        
                        # Add to recognition queue
                        if not self.recognition_queue.full():
                            self.recognition_queue.put({
                                'audio': enhanced_audio,
                                'timestamp': datetime.now(timezone.utc),
                                'sample_rate': self.sample_rate
                            })
                            
                        # Keep rolling buffer
                        audio_buffer = audio_buffer[-buffer_size//2:]
                        
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Audio processing error: {e}")
                await asyncio.sleep(1)
                
    async def recognition_loop(self):
        """Main speech recognition processing loop"""
        while self.is_running:
            try:
                if not self.recognition_queue.empty():
                    audio_data = self.recognition_queue.get_nowait()
                    
                    # Process with multiple recognition sources
                    recognition_tasks = [
                        self.openrouter_recognition(audio_data),
                        self.windows_speech_recognition(audio_data),
                        self.keyword_matching(audio_data)
                    ]
                    
                    # Wait for all recognition results
                    results = await asyncio.gather(*recognition_tasks, return_exceptions=True)
                    
                    # Calculate confidence and check for commands
                    await self.process_recognition_results(results, audio_data)
                    
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Recognition loop error: {e}")
                await asyncio.sleep(1)
                
    async def openrouter_recognition(self, audio_data: Dict) -> Optional[Dict]:
        """Process audio with OpenRouter.ai"""
        try:
            result = await self.openrouter_client.transcribe_audio(
                audio_data['audio'], 
                audio_data['sample_rate']
            )
            return result
        except Exception as e:
            self.logger.error(f"OpenRouter recognition error: {e}")
            return None
            
    async def windows_speech_recognition(self, audio_data: Dict) -> Optional[Dict]:
        """Process audio with Windows Speech Recognition"""
        try:
            result = await self.windows_speech.recognize_audio(
                audio_data['audio'], 
                audio_data['sample_rate']
            )
            return result
        except Exception as e:
            self.logger.error(f"Windows speech recognition error: {e}")
            return None
            
    async def keyword_matching(self, audio_data: Dict) -> Optional[Dict]:
        """Process audio with keyword matching fallback"""
        try:
            result = await self.keyword_matcher.match_keywords(
                audio_data['audio'], 
                audio_data['sample_rate']
            )
            return result
        except Exception as e:
            self.logger.error(f"Keyword matching error: {e}")
            return None
            
    async def process_recognition_results(self, results: List, audio_data: Dict):
        """Process recognition results and check for commands"""
        try:
            # Filter out exceptions and None results
            valid_results = [r for r in results if isinstance(r, dict) and r is not None]
            
            if not valid_results:
                return
                
            # Calculate weighted confidence
            total_confidence = 0
            total_weight = 0
            best_result = None
            
            weights = {
                'openrouter': 0.6,
                'windows_speech': 0.3,
                'keyword_exact': 0.1,
                'keyword_fuzzy': 0.05
            }
            
            for result in valid_results:
                source = result.get('source', 'unknown')
                confidence = result.get('confidence', 0)
                weight = weights.get(source, 0.1)
                
                total_confidence += confidence * weight
                total_weight += weight
                
                if not best_result or confidence > best_result.get('confidence', 0):
                    best_result = result
                    
            if total_weight > 0:
                final_confidence = total_confidence / total_weight
                
                # Check if confidence meets threshold
                if final_confidence > 0.6 and best_result:
                    await self.handle_command_detection(best_result, final_confidence)
                    
        except Exception as e:
            self.logger.error(f"Recognition result processing error: {e}")
            
    async def handle_command_detection(self, result: Dict, confidence: float):
        """Handle detected voice command"""
        try:
            command_text = result.get('text', '').lower().strip()
            matched_command = result.get('matched_command', command_text)
            
            self.logger.info(f"Command detected: '{command_text}' (confidence: {confidence:.2f})")
            
            # Send command to service via IPC
            message = IPCMessage("COMMAND_DETECTED", {
                'command': matched_command,
                'original_text': command_text,
                'confidence': confidence,
                'source': result.get('source', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            await self.ipc_client.send_message(message)
            
            # Update system tray
            self.system_tray.command_detected.emit(matched_command, confidence)
            
        except Exception as e:
            self.logger.error(f"Command detection handling error: {e}")
            
    async def status_reporting_loop(self):
        """Periodic status reporting to service"""
        while self.is_running:
            try:
                # Get audio statistics
                audio_stats = self.audio_processor.get_audio_statistics()
                
                # Get API key status
                api_status = await self.openrouter_client.get_status()
                
                # Send status update
                message = IPCMessage("STATUS_UPDATE", {
                    'component': 'audio_helper',
                    'status': 'running',
                    'audio_stats': audio_stats,
                    'api_status': api_status,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                await self.ipc_client.send_message(message)
                
                # Sleep for 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Status reporting error: {e}")
                await asyncio.sleep(60)
                
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up audio helper resources...")
        
        self.is_running = False
        
        if hasattr(self, 'ipc_client'):
            self.ipc_client.disconnect()
            
        if hasattr(self, 'openrouter_client'):
            await self.openrouter_client.cleanup()
            
        if hasattr(self, 'system_tray'):
            self.system_tray.quit()


if __name__ == '__main__':
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    helper = AudioHelperProcess()
    asyncio.run(helper.start())
