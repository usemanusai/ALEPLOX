#!/usr/bin/env python3
"""
VoiceGuard OpenRouter.ai Client
Smart API key rotation client for OpenRouter.ai speech recognition
"""

import aiohttp
import asyncio
import json
import base64
import hashlib
import sqlite3
import numpy as np
import io
import wave
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from pathlib import Path
import logging


class OpenRouterClient:
    """Smart API key rotation client for OpenRouter.ai"""
    
    def __init__(self):
        self.api_keys = []
        self.current_key_index = 0
        self.daily_limit = 50
        self.session = None
        self.base_url = "https://openrouter.ai/api/v1"
        self.db_path = Path("C:/ProgramData/VoiceGuard/config.db")
        self.logger = logging.getLogger("OpenRouterClient")
        
    async def initialize(self):
        """Initialize OpenRouter client with API keys"""
        # Create HTTP session with optimized settings
        timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'VoiceGuard/1.0',
                'Content-Type': 'application/json'
            }
        )
        
        # Load API keys from database
        await self.load_api_keys()
        
    async def load_api_keys(self):
        """Load and decrypt API keys from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT id, key_hash, encrypted_key, daily_usage, last_reset_date, is_active "
                    "FROM api_keys WHERE is_active = 1 ORDER BY daily_usage ASC"
                )
                
                self.api_keys = []
                for row in cursor.fetchall():
                    key_id, key_hash, encrypted_key, daily_usage, last_reset_date, is_active = row
                    
                    # Decrypt API key
                    try:
                        from config_manager import ConfigurationManager
                        config_manager = ConfigurationManager()
                        decrypted_key = config_manager.decrypt_value(encrypted_key)
                        
                        self.api_keys.append({
                            'id': key_id,
                            'key': decrypted_key,
                            'hash': key_hash,
                            'daily_usage': daily_usage,
                            'last_reset_date': datetime.fromisoformat(last_reset_date).date(),
                            'last_used': None
                        })
                    except Exception as e:
                        self.logger.error(f"Failed to decrypt API key {key_id}: {e}")
                        
            self.logger.info(f"Loaded {len(self.api_keys)} API keys")
            
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            self.api_keys = []
                
    async def get_available_key(self) -> Optional[Dict]:
        """Get next available API key with smart rotation"""
        if not self.api_keys:
            return None
            
        current_date = datetime.now(timezone.utc).date()
        
        # Reset daily counters if new day
        for key in self.api_keys:
            if key['last_reset_date'] < current_date:
                key['daily_usage'] = 0
                key['last_reset_date'] = current_date
                await self.update_key_usage(key['id'], 0, current_date)
        
        # Find available keys (not at daily limit)
        available_keys = [
            key for key in self.api_keys 
            if key['daily_usage'] < self.daily_limit
        ]
        
        if not available_keys:
            return None  # All keys exhausted
            
        # Rate limiting: don't use same key within 6 seconds
        now = datetime.now(timezone.utc)
        available_keys = [
            key for key in available_keys
            if not key['last_used'] or (now - key['last_used']).total_seconds() >= 6
        ]
        
        if not available_keys:
            # Wait for rate limit to clear
            await asyncio.sleep(1)
            return await self.get_available_key()
            
        # Select key with lowest usage (load balancing)
        selected_key = min(available_keys, key=lambda k: k['daily_usage'])
        selected_key['last_used'] = now
        
        return selected_key
        
    async def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int) -> Optional[Dict]:
        """Transcribe audio using OpenRouter.ai Whisper"""
        try:
            # Get available API key
            api_key = await self.get_available_key()
            if not api_key:
                self.logger.warning("No API keys available")
                return None  # No keys available
                
            # Convert audio to WAV format for API
            audio_bytes = self.audio_to_wav_bytes(audio_data, sample_rate)
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Prepare API request
            payload = {
                'model': 'openai/whisper-large-v3',
                'audio': audio_b64,
                'response_format': 'json',
                'language': 'en',
                'temperature': 0.0  # Deterministic output
            }
            
            headers = {
                'Authorization': f'Bearer {api_key["key"]}',
                'HTTP-Referer': 'https://voiceguard.local',
                'X-Title': 'VoiceGuard Emergency System'
            }
            
            # Make API request
            async with self.session.post(
                f"{self.base_url}/audio/transcriptions",
                json=payload,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Update key usage
                    api_key['daily_usage'] += 1
                    await self.update_key_usage(api_key['id'], api_key['daily_usage'])
                    
                    return {
                        'text': result.get('text', '').strip(),
                        'confidence': 0.9,  # OpenRouter doesn't provide confidence
                        'source': 'openrouter',
                        'model': 'whisper-large-v3'
                    }
                    
                elif response.status == 429:
                    # Rate limited - mark key as temporarily unavailable
                    api_key['daily_usage'] = self.daily_limit
                    await self.update_key_usage(api_key['id'], self.daily_limit)
                    self.logger.warning(f"API key {api_key['hash']} rate limited")
                    return None
                    
                else:
                    error_text = await response.text()
                    self.logger.warning(f"OpenRouter API error {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            self.logger.warning("OpenRouter API timeout")
            return None
        except Exception as e:
            self.logger.error(f"OpenRouter transcription error: {e}")
            return None
            
    def audio_to_wav_bytes(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy audio array to WAV bytes"""
        # Ensure audio is 16-bit
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
            
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
            
        return wav_buffer.getvalue()
        
    async def update_key_usage(self, key_id: int, usage: int, reset_date: Optional[datetime.date] = None):
        """Update API key usage in database"""
        try:
            if reset_date:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE api_keys SET daily_usage = ?, last_reset_date = ?, last_used = ? WHERE id = ?",
                        (usage, reset_date.isoformat(), datetime.now(timezone.utc).isoformat(), key_id)
                    )
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE api_keys SET daily_usage = ?, last_used = ? WHERE id = ?",
                        (usage, datetime.now(timezone.utc).isoformat(), key_id)
                    )
        except Exception as e:
            self.logger.error(f"Failed to update key usage: {e}")
            
    async def get_status(self) -> Dict:
        """Get current API key status"""
        if not self.api_keys:
            return {
                'total_keys': 0,
                'active_keys': 0,
                'daily_usage': 0,
                'daily_limit': 0,
                'keys_available': 0
            }
            
        total_usage = sum(key['daily_usage'] for key in self.api_keys)
        total_limit = len(self.api_keys) * self.daily_limit
        available_keys = len([key for key in self.api_keys if key['daily_usage'] < self.daily_limit])
        
        return {
            'total_keys': len(self.api_keys),
            'active_keys': len(self.api_keys),
            'daily_usage': total_usage,
            'daily_limit': total_limit,
            'keys_available': available_keys
        }
        
    async def test_api_key(self, api_key: str) -> bool:
        """Test if an API key is valid"""
        try:
            # Create a small test audio (1 second of silence)
            test_audio = np.zeros(16000, dtype=np.int16)
            audio_bytes = self.audio_to_wav_bytes(test_audio, 16000)
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            payload = {
                'model': 'openai/whisper-large-v3',
                'audio': audio_b64,
                'response_format': 'json',
                'language': 'en'
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'HTTP-Referer': 'https://voiceguard.local',
                'X-Title': 'VoiceGuard Test'
            }
            
            async with self.session.post(
                f"{self.base_url}/audio/transcriptions",
                json=payload,
                headers=headers
            ) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"API key test error: {e}")
            return False
            
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
