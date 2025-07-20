#!/usr/bin/env python3
"""
VoiceGuard Keyword Matcher
Fast keyword matching for emergency fallback recognition
"""

import re
import difflib
from typing import List, Dict, Optional
import logging
import numpy as np


class KeywordMatcher:
    """Fast keyword matching for emergency fallback"""
    
    def __init__(self):
        self.logger = logging.getLogger("KeywordMatcher")
        self.commands = []
        self.phonetic_patterns = {}
        
    def set_commands(self, commands: List[str]):
        """Set the list of commands to match against"""
        self.commands = [cmd.lower().strip() for cmd in commands]
        self._build_phonetic_patterns()
        
    def _build_phonetic_patterns(self):
        """Build phonetic patterns for better matching"""
        # Simple phonetic replacements for common speech recognition errors
        phonetic_replacements = {
            'emergency': ['emerjency', 'emergancy', 'emargency'],
            'shutdown': ['shutdoun', 'shut down', 'shotdown'],
            'kill': ['kil', 'kell'],
            'switch': ['swich', 'swithc'],
            'force': ['forse', 'fource'],
            'stop': ['stap', 'stup']
        }
        
        for command in self.commands:
            patterns = [command]
            
            # Add phonetic variations
            for word, variations in phonetic_replacements.items():
                if word in command:
                    for variation in variations:
                        patterns.append(command.replace(word, variation))
                        
            self.phonetic_patterns[command] = patterns
            
    async def match_keywords(self, audio_data: np.ndarray, sample_rate: int) -> Optional[Dict]:
        """Simple keyword matching (placeholder for actual implementation)"""
        # This is a simplified implementation
        # In a real system, you might use phonetic matching or other techniques
        
        # For now, we'll return None since we don't have actual audio-to-text
        # conversion in this fallback method
        return None
        
    def match_text(self, text: str) -> Optional[Dict]:
        """Match text against configured commands"""
        if not text or not self.commands:
            return None
            
        text = text.lower().strip()
        best_match = None
        best_ratio = 0
        match_type = None
        
        for command in self.commands:
            # Exact match
            if text == command:
                return {
                    'text': text,
                    'matched_command': command,
                    'confidence': 1.0,
                    'source': 'keyword_exact',
                    'method': 'exact_match'
                }
                
            # Substring match
            if command in text or text in command:
                ratio = 0.9
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = command
                    match_type = 'substring_match'
                    
            # Fuzzy match using difflib
            ratio = difflib.SequenceMatcher(None, text, command).ratio()
            if ratio > best_ratio and ratio > 0.7:
                best_ratio = ratio
                best_match = command
                match_type = 'fuzzy_match'
                
            # Phonetic pattern matching
            if command in self.phonetic_patterns:
                for pattern in self.phonetic_patterns[command]:
                    ratio = difflib.SequenceMatcher(None, text, pattern).ratio()
                    if ratio > best_ratio and ratio > 0.8:
                        best_ratio = ratio
                        best_match = command
                        match_type = 'phonetic_match'
                        
            # Word-based matching
            text_words = set(text.split())
            command_words = set(command.split())
            
            if text_words and command_words:
                intersection = text_words.intersection(command_words)
                union = text_words.union(command_words)
                
                if intersection:
                    word_ratio = len(intersection) / len(union)
                    if word_ratio > best_ratio and word_ratio > 0.6:
                        best_ratio = word_ratio
                        best_match = command
                        match_type = 'word_match'
                        
        if best_match and best_ratio > 0.6:
            return {
                'text': text,
                'matched_command': best_match,
                'confidence': best_ratio,
                'source': 'keyword_fuzzy',
                'method': match_type
            }
            
        return None
        
    def match_partial(self, text: str, min_confidence: float = 0.5) -> List[Dict]:
        """Match text against commands and return all matches above threshold"""
        if not text or not self.commands:
            return []
            
        text = text.lower().strip()
        matches = []
        
        for command in self.commands:
            best_ratio = 0
            match_type = None
            
            # Exact match
            if text == command:
                matches.append({
                    'text': text,
                    'matched_command': command,
                    'confidence': 1.0,
                    'source': 'keyword_exact',
                    'method': 'exact_match'
                })
                continue
                
            # Substring match
            if command in text or text in command:
                ratio = 0.9
                if ratio > best_ratio:
                    best_ratio = ratio
                    match_type = 'substring_match'
                    
            # Fuzzy match
            ratio = difflib.SequenceMatcher(None, text, command).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                match_type = 'fuzzy_match'
                
            # Phonetic matching
            if command in self.phonetic_patterns:
                for pattern in self.phonetic_patterns[command]:
                    ratio = difflib.SequenceMatcher(None, text, pattern).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        match_type = 'phonetic_match'
                        
            if best_ratio >= min_confidence:
                matches.append({
                    'text': text,
                    'matched_command': command,
                    'confidence': best_ratio,
                    'source': 'keyword_fuzzy',
                    'method': match_type
                })
                
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches
        
    def add_command_variations(self, command: str, variations: List[str]):
        """Add custom variations for a command"""
        if command in self.phonetic_patterns:
            self.phonetic_patterns[command].extend(variations)
        else:
            self.phonetic_patterns[command] = [command] + variations
            
    def test_command_matching(self, test_phrases: List[str]) -> Dict:
        """Test command matching with various phrases"""
        results = {}
        
        for phrase in test_phrases:
            match = self.match_text(phrase)
            results[phrase] = match
            
        return results
        
    def get_command_statistics(self) -> Dict:
        """Get statistics about configured commands"""
        if not self.commands:
            return {
                'total_commands': 0,
                'average_length': 0,
                'phonetic_patterns': 0
            }
            
        total_length = sum(len(cmd) for cmd in self.commands)
        average_length = total_length / len(self.commands)
        
        total_patterns = sum(len(patterns) for patterns in self.phonetic_patterns.values())
        
        return {
            'total_commands': len(self.commands),
            'average_length': average_length,
            'phonetic_patterns': total_patterns,
            'commands': self.commands.copy()
        }
        
    def optimize_patterns(self):
        """Optimize phonetic patterns for better performance"""
        # Remove duplicate patterns
        for command in self.phonetic_patterns:
            patterns = list(set(self.phonetic_patterns[command]))
            self.phonetic_patterns[command] = patterns
            
        self.logger.info("Phonetic patterns optimized")
        
    def export_patterns(self) -> Dict:
        """Export phonetic patterns for backup/sharing"""
        return {
            'commands': self.commands.copy(),
            'phonetic_patterns': self.phonetic_patterns.copy()
        }
        
    def import_patterns(self, patterns_data: Dict):
        """Import phonetic patterns from backup/sharing"""
        if 'commands' in patterns_data:
            self.commands = patterns_data['commands']
            
        if 'phonetic_patterns' in patterns_data:
            self.phonetic_patterns = patterns_data['phonetic_patterns']
            
        self.logger.info("Phonetic patterns imported")
        
    def clear_patterns(self):
        """Clear all patterns and commands"""
        self.commands.clear()
        self.phonetic_patterns.clear()
        self.logger.info("All patterns cleared")
