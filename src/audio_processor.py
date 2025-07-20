#!/usr/bin/env python3
"""
VoiceGuard Audio Processor
Advanced audio processing for voice activity detection and enhancement
"""

import numpy as np
import scipy.signal
import collections
import threading
import logging
from typing import Optional, Tuple, List
import time

try:
    import webrtcvad
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


class AudioProcessor:
    """Advanced audio processing for voice activity detection and enhancement"""
    
    def __init__(self):
        self.logger = logging.getLogger("AudioProcessor")
        
        # Audio parameters
        self.sample_rate = 16000
        self.frame_duration_ms = 30  # 30ms frames for WebRTC VAD
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        # Voice Activity Detection
        if WEBRTC_AVAILABLE:
            self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (0-3)
        else:
            self.vad = None
            self.logger.warning("WebRTC VAD not available, using simple energy-based VAD")
        
        # Audio enhancement
        self.noise_profile = None
        self.noise_gate_threshold = -40  # dB
        self.auto_gain_target = -12  # dB
        
        # Circular buffer for continuous processing
        self.audio_buffer = collections.deque(maxlen=self.sample_rate * 10)  # 10 seconds
        self.buffer_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'voice_frames': 0,
            'noise_frames': 0,
            'avg_volume': 0.0,
            'peak_volume': 0.0
        }
        
    def detect_voice_activity(self, audio_data: np.ndarray) -> bool:
        """Detect voice activity in audio data"""
        try:
            # Ensure audio is 16-bit PCM
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
                
            if self.vad and WEBRTC_AVAILABLE:
                return self._webrtc_vad(audio_data)
            else:
                return self._energy_based_vad(audio_data)
                
        except Exception as e:
            self.logger.error(f"Voice activity detection error: {e}")
            return False
            
    def _webrtc_vad(self, audio_data: np.ndarray) -> bool:
        """WebRTC-based voice activity detection"""
        # Process in 30ms frames for WebRTC VAD
        frame_count = len(audio_data) // self.frame_size
        voice_frames = 0
        
        for i in range(frame_count):
            start_idx = i * self.frame_size
            end_idx = start_idx + self.frame_size
            frame = audio_data[start_idx:end_idx]
            
            # WebRTC VAD requires exactly frame_size samples
            if len(frame) == self.frame_size:
                frame_bytes = frame.tobytes()
                is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
                
                if is_speech:
                    voice_frames += 1
                    
        # Update statistics
        self.stats['frames_processed'] += frame_count
        self.stats['voice_frames'] += voice_frames
        self.stats['noise_frames'] += (frame_count - voice_frames)
        
        # Consider voice active if >30% of frames contain speech
        voice_ratio = voice_frames / frame_count if frame_count > 0 else 0
        return voice_ratio > 0.3
        
    def _energy_based_vad(self, audio_data: np.ndarray) -> bool:
        """Simple energy-based voice activity detection"""
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        
        # Convert to dB
        rms_db = 20 * np.log10(rms + 1e-10)
        
        # Update statistics
        self.stats['frames_processed'] += 1
        self.stats['avg_volume'] = 0.9 * self.stats['avg_volume'] + 0.1 * rms_db
        self.stats['peak_volume'] = max(self.stats['peak_volume'], rms_db)
        
        # Simple threshold-based detection
        voice_threshold = -30  # dB
        is_voice = rms_db > voice_threshold
        
        if is_voice:
            self.stats['voice_frames'] += 1
        else:
            self.stats['noise_frames'] += 1
            
        return is_voice
        
    def enhance_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Enhance audio quality for better recognition"""
        try:
            # Convert to float for processing
            audio_float = audio_data.astype(np.float32) / 32767.0
            
            # Apply noise gate
            audio_float = self._apply_noise_gate(audio_float)
            
            # Apply noise reduction if profile available
            if self.noise_profile is not None and LIBROSA_AVAILABLE:
                audio_float = self._apply_noise_reduction(audio_float)
                
            # Apply automatic gain control
            audio_float = self._apply_auto_gain(audio_float)
            
            # Apply high-pass filter to remove low-frequency noise
            audio_float = self._apply_high_pass_filter(audio_float)
            
            # Convert back to int16
            enhanced_audio = (audio_float * 32767).astype(np.int16)
            
            return enhanced_audio
            
        except Exception as e:
            self.logger.error(f"Audio enhancement error: {e}")
            return audio_data
            
    def _apply_noise_gate(self, audio: np.ndarray) -> np.ndarray:
        """Apply noise gate to reduce background noise"""
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)
        
        # Apply gate
        if rms_db < self.noise_gate_threshold:
            return audio * 0.1  # Reduce by 20dB
        else:
            return audio
            
    def _apply_noise_reduction(self, audio: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction noise reduction"""
        if not LIBROSA_AVAILABLE:
            return audio
            
        try:
            # Perform STFT
            stft = librosa.stft(audio, n_fft=1024, hop_length=256)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Spectral subtraction
            noise_magnitude = self.noise_profile
            alpha = 2.0  # Over-subtraction factor
            
            # Subtract noise spectrum
            clean_magnitude = magnitude - alpha * noise_magnitude
            
            # Ensure non-negative values
            clean_magnitude = np.maximum(clean_magnitude, 0.1 * magnitude)
            
            # Reconstruct signal
            clean_stft = clean_magnitude * np.exp(1j * phase)
            clean_audio = librosa.istft(clean_stft, hop_length=256)
            
            return clean_audio
            
        except Exception as e:
            self.logger.error(f"Noise reduction error: {e}")
            return audio
            
    def _apply_auto_gain(self, audio: np.ndarray) -> np.ndarray:
        """Apply automatic gain control"""
        # Calculate current RMS level
        rms = np.sqrt(np.mean(audio ** 2))
        current_db = 20 * np.log10(rms + 1e-10)
        
        # Calculate required gain
        gain_db = self.auto_gain_target - current_db
        gain_linear = 10 ** (gain_db / 20)
        
        # Limit gain to prevent distortion
        gain_linear = np.clip(gain_linear, 0.1, 10.0)
        
        return audio * gain_linear
        
    def _apply_high_pass_filter(self, audio: np.ndarray) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise"""
        # Design high-pass filter (80 Hz cutoff)
        nyquist = self.sample_rate / 2
        cutoff = 80 / nyquist
        
        b, a = scipy.signal.butter(4, cutoff, btype='high')
        filtered_audio = scipy.signal.filtfilt(b, a, audio)
        
        return filtered_audio
        
    def learn_noise_profile(self, noise_audio: np.ndarray):
        """Learn noise profile from background noise sample"""
        if not LIBROSA_AVAILABLE:
            self.logger.warning("Librosa not available, noise profiling disabled")
            return
            
        try:
            # Convert to float
            noise_float = noise_audio.astype(np.float32) / 32767.0
            
            # Compute magnitude spectrum
            stft = librosa.stft(noise_float, n_fft=1024, hop_length=256)
            noise_magnitude = np.mean(np.abs(stft), axis=1, keepdims=True)
            
            self.noise_profile = noise_magnitude
            self.logger.info("Noise profile learned successfully")
            
        except Exception as e:
            self.logger.error(f"Noise profile learning error: {e}")
            
    def add_to_buffer(self, audio_data: np.ndarray):
        """Add audio data to circular buffer"""
        with self.buffer_lock:
            self.audio_buffer.extend(audio_data)
            
    def get_buffer_data(self, duration_seconds: float) -> np.ndarray:
        """Get audio data from buffer"""
        with self.buffer_lock:
            samples_needed = int(duration_seconds * self.sample_rate)
            
            if len(self.audio_buffer) >= samples_needed:
                # Get last N seconds of audio
                buffer_array = np.array(list(self.audio_buffer))
                return buffer_array[-samples_needed:]
            else:
                # Return all available data
                return np.array(list(self.audio_buffer))
                
    def get_audio_statistics(self) -> dict:
        """Get audio processing statistics"""
        total_frames = self.stats['frames_processed']
        
        if total_frames > 0:
            voice_ratio = self.stats['voice_frames'] / total_frames
            noise_ratio = self.stats['noise_frames'] / total_frames
        else:
            voice_ratio = 0.0
            noise_ratio = 0.0
            
        return {
            'frames_processed': total_frames,
            'voice_activity_ratio': voice_ratio,
            'noise_ratio': noise_ratio,
            'average_volume': self.stats['avg_volume'],
            'peak_volume': self.stats['peak_volume'],
            'webrtc_available': WEBRTC_AVAILABLE,
            'librosa_available': LIBROSA_AVAILABLE
        }
        
    def reset_statistics(self):
        """Reset audio processing statistics"""
        self.stats = {
            'frames_processed': 0,
            'voice_frames': 0,
            'noise_frames': 0,
            'avg_volume': 0.0,
            'peak_volume': 0.0
        }
        
    def configure_vad(self, aggressiveness: int = 2):
        """Configure VAD aggressiveness (0-3, higher = more aggressive)"""
        if WEBRTC_AVAILABLE and self.vad:
            self.vad = webrtcvad.Vad(aggressiveness)
            self.logger.info(f"VAD aggressiveness set to {aggressiveness}")
        else:
            self.logger.warning("WebRTC VAD not available")
            
    def configure_enhancement(self, **kwargs):
        """Configure audio enhancement parameters"""
        if 'noise_gate_threshold' in kwargs:
            self.noise_gate_threshold = kwargs['noise_gate_threshold']
            
        if 'auto_gain_target' in kwargs:
            self.auto_gain_target = kwargs['auto_gain_target']
            
        self.logger.info(f"Audio enhancement configured: {kwargs}")
