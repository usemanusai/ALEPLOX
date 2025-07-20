#!/usr/bin/env python3
"""
VoiceGuard Configuration Manager
Manages VoiceGuard configuration with encryption and validation
"""

import json
import sqlite3
import win32crypt
from pathlib import Path
from typing import Any, Dict, List
import threading
import logging


class ConfigurationManager:
    """Manages VoiceGuard configuration with encryption and validation"""
    
    def __init__(self):
        self.config_path = Path("C:/ProgramData/VoiceGuard")
        self.db_path = self.config_path / "config.db"
        self.config_lock = threading.RLock()
        self.cache = {}
        self.logger = logging.getLogger("ConfigManager")
        
    def initialize(self):
        """Initialize configuration system"""
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.create_database()
        self.load_default_config()
        
    def create_database(self):
        """Create SQLite database for configuration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS voice_commands (
                    id INTEGER PRIMARY KEY,
                    command_text TEXT UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    confidence_threshold REAL DEFAULT 0.5,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    encrypted_key BLOB NOT NULL,
                    daily_usage INTEGER DEFAULT 0,
                    last_reset_date DATE DEFAULT CURRENT_DATE,
                    is_active BOOLEAN DEFAULT 1,
                    last_used TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    data_type TEXT DEFAULT 'string',
                    encrypted BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    confidence_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
    def load_default_config(self):
        """Load default configuration settings"""
        defaults = {
            "test_mode": False,
            "confirmation_delay": 3,
            "microphone_sensitivity": 0.8,
            "confidence_threshold": 0.6,
            "noise_suppression": True,
            "voice_activity_detection": True,
            "quiet_hours_enabled": False,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "06:00",
            "max_daily_api_calls": 1500,
            "api_timeout": 5.0,
            "fallback_to_windows_speech": True
        }
        
        with sqlite3.connect(self.db_path) as conn:
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value, data_type) VALUES (?, ?, ?)",
                    (key, json.dumps(value), type(value).__name__)
                )
                
        # Load default voice commands
        default_commands = [
            "emergency shutdown",
            "kill switch", 
            "force stop",
            "shutdown now"
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for command in default_commands:
                conn.execute(
                    "INSERT OR IGNORE INTO voice_commands (command_text) VALUES (?)",
                    (command,)
                )
                
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting with caching"""
        with self.config_lock:
            if key in self.cache:
                return self.cache[key]
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value, data_type, encrypted FROM settings WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if row:
                    value, data_type, encrypted = row
                    
                    if encrypted:
                        value = self.decrypt_value(value)
                        
                    # Convert back to original type
                    if data_type == 'bool':
                        value = json.loads(value)
                    elif data_type == 'int':
                        value = int(json.loads(value))
                    elif data_type == 'float':
                        value = float(json.loads(value))
                    else:
                        value = json.loads(value)
                        
                    self.cache[key] = value
                    return value
                    
                return default
                
    def set_setting(self, key: str, value: Any, encrypt: bool = False):
        """Set configuration setting"""
        with self.config_lock:
            json_value = json.dumps(value)
            data_type = type(value).__name__
            
            if encrypt:
                json_value = self.encrypt_value(json_value)
                
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value, data_type, encrypted) VALUES (?, ?, ?, ?)",
                    (key, json_value, data_type, encrypt)
                )
                
            # Update cache
            self.cache[key] = value
            
    def get_voice_commands(self) -> List[Dict]:
        """Get all voice commands"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, command_text, enabled, confidence_threshold, created_date "
                "FROM voice_commands ORDER BY command_text"
            )
            
            commands = []
            for row in cursor.fetchall():
                commands.append({
                    'id': row[0],
                    'command_text': row[1],
                    'enabled': bool(row[2]),
                    'confidence_threshold': row[3],
                    'created_date': row[4]
                })
                
            return commands
            
    def add_voice_command(self, command_text: str, confidence_threshold: float = 0.6) -> bool:
        """Add a new voice command"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO voice_commands (command_text, confidence_threshold) VALUES (?, ?)",
                    (command_text.strip().lower(), confidence_threshold)
                )
            return True
        except sqlite3.IntegrityError:
            return False  # Command already exists
            
    def remove_voice_command(self, command_id: int) -> bool:
        """Remove a voice command"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM voice_commands WHERE id = ?",
                (command_id,)
            )
            return cursor.rowcount > 0
            
    def update_voice_command(self, command_id: int, **kwargs) -> bool:
        """Update a voice command"""
        if not kwargs:
            return False
            
        # Build update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['command_text', 'enabled', 'confidence_threshold']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
                
        if not set_clauses:
            return False
            
        values.append(command_id)
        query = f"UPDATE voice_commands SET {', '.join(set_clauses)} WHERE id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, values)
            return cursor.rowcount > 0
            
    def add_api_key(self, api_key: str) -> bool:
        """Add an encrypted API key"""
        try:
            key_hash = self.hash_api_key(api_key)
            encrypted_key = self.encrypt_value(api_key)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO api_keys (key_hash, encrypted_key) VALUES (?, ?)",
                    (key_hash, encrypted_key)
                )
            return True
        except sqlite3.IntegrityError:
            return False  # Key already exists
            
    def get_api_keys(self) -> List[Dict]:
        """Get all API keys (encrypted)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, key_hash, daily_usage, last_reset_date, is_active, last_used "
                "FROM api_keys WHERE is_active = 1 ORDER BY daily_usage ASC"
            )
            
            keys = []
            for row in cursor.fetchall():
                keys.append({
                    'id': row[0],
                    'key_hash': row[1],
                    'daily_usage': row[2],
                    'last_reset_date': row[3],
                    'is_active': bool(row[4]),
                    'last_used': row[5]
                })
                
            return keys
            
    def encrypt_value(self, value: str) -> bytes:
        """Encrypt sensitive configuration values using DPAPI"""
        return win32crypt.CryptProtectData(
            value.encode('utf-8'),
            "VoiceGuard Configuration",
            None,
            None,
            None,
            win32crypt.CRYPTPROTECT_LOCAL_MACHINE
        )
        
    def decrypt_value(self, encrypted_value: bytes) -> str:
        """Decrypt sensitive configuration values"""
        decrypted = win32crypt.CryptUnprotectData(
            encrypted_value,
            None,
            None,
            None,
            0
        )
        return decrypted[1].decode('utf-8')
        
    def hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for identification"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
    def reload_configuration(self):
        """Reload configuration from database"""
        with self.config_lock:
            self.cache.clear()
            self.logger.info("Configuration reloaded")
            
    def backup_configuration(self, backup_path: Path) -> bool:
        """Backup configuration to file"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            self.logger.error(f"Configuration backup failed: {e}")
            return False
            
    def restore_configuration(self, backup_path: Path) -> bool:
        """Restore configuration from backup"""
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            self.reload_configuration()
            return True
        except Exception as e:
            self.logger.error(f"Configuration restore failed: {e}")
            return False
