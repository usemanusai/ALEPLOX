#!/usr/bin/env python3
"""
Tests for VoiceGuard Configuration Manager
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigurationManager


class TestConfigurationManager:
    """Test cases for ConfigurationManager"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_config.db"
        
        # Create config manager with test database
        self.config_manager = ConfigurationManager()
        self.config_manager.db_path = self.test_db_path
        self.config_manager.config_path = Path(self.temp_dir)
        
    def teardown_method(self):
        """Cleanup after each test"""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_initialize_creates_database(self):
        """Test that initialize creates the database and tables"""
        self.config_manager.initialize()
        
        # Check that database file exists
        assert self.test_db_path.exists()
        
        # Check that tables were created
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
        expected_tables = ['voice_commands', 'api_keys', 'settings', 'event_log']
        for table in expected_tables:
            assert table in tables
            
    def test_load_default_config(self):
        """Test that default configuration is loaded"""
        self.config_manager.initialize()
        
        # Check default settings
        test_mode = self.config_manager.get_setting("test_mode")
        assert test_mode is False
        
        confidence = self.config_manager.get_setting("confidence_threshold")
        assert confidence == 0.6
        
        # Check default commands
        commands = self.config_manager.get_voice_commands()
        assert len(commands) > 0
        
        command_texts = [cmd['command_text'] for cmd in commands]
        assert "emergency shutdown" in command_texts
        
    def test_get_set_setting(self):
        """Test getting and setting configuration values"""
        self.config_manager.initialize()
        
        # Test setting and getting string value
        self.config_manager.set_setting("test_string", "hello world")
        result = self.config_manager.get_setting("test_string")
        assert result == "hello world"
        
        # Test setting and getting boolean value
        self.config_manager.set_setting("test_bool", True)
        result = self.config_manager.get_setting("test_bool")
        assert result is True
        
        # Test setting and getting numeric value
        self.config_manager.set_setting("test_float", 3.14)
        result = self.config_manager.get_setting("test_float")
        assert result == 3.14
        
    def test_get_setting_default_value(self):
        """Test getting setting with default value"""
        self.config_manager.initialize()
        
        # Test non-existent setting returns default
        result = self.config_manager.get_setting("nonexistent", "default_value")
        assert result == "default_value"
        
        # Test non-existent setting returns None when no default
        result = self.config_manager.get_setting("nonexistent")
        assert result is None
        
    def test_voice_commands_crud(self):
        """Test CRUD operations for voice commands"""
        self.config_manager.initialize()
        
        # Test adding command
        success = self.config_manager.add_voice_command("test command", 0.8)
        assert success is True
        
        # Test getting commands
        commands = self.config_manager.get_voice_commands()
        test_commands = [cmd for cmd in commands if cmd['command_text'] == "test command"]
        assert len(test_commands) == 1
        assert test_commands[0]['confidence_threshold'] == 0.8
        
        # Test updating command
        command_id = test_commands[0]['id']
        success = self.config_manager.update_voice_command(
            command_id, 
            confidence_threshold=0.9,
            enabled=False
        )
        assert success is True
        
        # Verify update
        commands = self.config_manager.get_voice_commands()
        updated_command = next(cmd for cmd in commands if cmd['id'] == command_id)
        assert updated_command['confidence_threshold'] == 0.9
        assert updated_command['enabled'] is False
        
        # Test removing command
        success = self.config_manager.remove_voice_command(command_id)
        assert success is True
        
        # Verify removal
        commands = self.config_manager.get_voice_commands()
        remaining_commands = [cmd for cmd in commands if cmd['id'] == command_id]
        assert len(remaining_commands) == 0
        
    def test_add_duplicate_command_fails(self):
        """Test that adding duplicate command fails"""
        self.config_manager.initialize()
        
        # Add first command
        success = self.config_manager.add_voice_command("duplicate test")
        assert success is True
        
        # Try to add duplicate
        success = self.config_manager.add_voice_command("duplicate test")
        assert success is False
        
    @patch('win32crypt.CryptProtectData')
    @patch('win32crypt.CryptUnprotectData')
    def test_encrypted_settings(self, mock_decrypt, mock_encrypt):
        """Test encrypted setting storage"""
        self.config_manager.initialize()
        
        # Mock encryption/decryption
        mock_encrypt.return_value = b'encrypted_data'
        mock_decrypt.return_value = (None, b'{"sensitive_value": "secret"}')
        
        # Test setting encrypted value
        self.config_manager.set_setting("api_key", "secret_key", encrypt=True)
        
        # Verify encryption was called
        mock_encrypt.assert_called_once()
        
        # Test getting encrypted value
        result = self.config_manager.get_setting("api_key")
        
        # Verify decryption was called
        mock_decrypt.assert_called_once()
        
    def test_setting_caching(self):
        """Test that settings are cached properly"""
        self.config_manager.initialize()
        
        # Set a value
        self.config_manager.set_setting("cached_value", "test")
        
        # Get value (should be cached)
        result1 = self.config_manager.get_setting("cached_value")
        result2 = self.config_manager.get_setting("cached_value")
        
        assert result1 == "test"
        assert result2 == "test"
        
        # Verify value is in cache
        assert "cached_value" in self.config_manager.cache
        
    def test_reload_configuration(self):
        """Test configuration reload clears cache"""
        self.config_manager.initialize()
        
        # Set and cache a value
        self.config_manager.set_setting("test_reload", "original")
        cached_value = self.config_manager.get_setting("test_reload")
        assert cached_value == "original"
        assert "test_reload" in self.config_manager.cache
        
        # Reload configuration
        self.config_manager.reload_configuration()
        
        # Verify cache is cleared
        assert len(self.config_manager.cache) == 0
        
    def test_backup_restore_configuration(self):
        """Test configuration backup and restore"""
        self.config_manager.initialize()
        
        # Add some test data
        self.config_manager.set_setting("backup_test", "test_value")
        self.config_manager.add_voice_command("backup command")
        
        # Create backup
        backup_path = Path(self.temp_dir) / "backup.db"
        success = self.config_manager.backup_configuration(backup_path)
        assert success is True
        assert backup_path.exists()
        
        # Modify original data
        self.config_manager.set_setting("backup_test", "modified_value")
        
        # Restore from backup
        success = self.config_manager.restore_configuration(backup_path)
        assert success is True
        
        # Verify restoration
        restored_value = self.config_manager.get_setting("backup_test")
        assert restored_value == "test_value"


class TestConfigurationManagerIntegration:
    """Integration tests for ConfigurationManager"""
    
    def setup_method(self):
        """Setup for integration tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigurationManager()
        self.config_manager.config_path = Path(self.temp_dir)
        self.config_manager.db_path = Path(self.temp_dir) / "integration_test.db"
        
    def teardown_method(self):
        """Cleanup after integration tests"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_full_configuration_workflow(self):
        """Test complete configuration workflow"""
        # Initialize
        self.config_manager.initialize()
        
        # Configure voice commands
        commands_to_add = [
            ("custom shutdown", 0.7),
            ("emergency stop", 0.8),
            ("force quit", 0.6)
        ]
        
        for command, confidence in commands_to_add:
            success = self.config_manager.add_voice_command(command, confidence)
            assert success is True
            
        # Configure settings
        settings_to_set = {
            "test_mode": True,
            "microphone_sensitivity": 0.9,
            "confirmation_delay": 5,
            "api_timeout": 10.0
        }
        
        for key, value in settings_to_set.items():
            self.config_manager.set_setting(key, value)
            
        # Verify all data
        commands = self.config_manager.get_voice_commands()
        custom_commands = [
            cmd for cmd in commands 
            if cmd['command_text'] in [c[0] for c in commands_to_add]
        ]
        assert len(custom_commands) == 3
        
        for key, expected_value in settings_to_set.items():
            actual_value = self.config_manager.get_setting(key)
            assert actual_value == expected_value
            
        # Test backup and restore
        backup_path = Path(self.temp_dir) / "workflow_backup.db"
        success = self.config_manager.backup_configuration(backup_path)
        assert success is True
        
        # Modify data
        self.config_manager.set_setting("test_mode", False)
        
        # Restore and verify
        success = self.config_manager.restore_configuration(backup_path)
        assert success is True
        
        restored_test_mode = self.config_manager.get_setting("test_mode")
        assert restored_test_mode is True


if __name__ == '__main__':
    pytest.main([__file__])
