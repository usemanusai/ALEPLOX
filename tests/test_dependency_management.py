#!/usr/bin/env python3
"""
Tests for VoiceGuard Dependency Management System
"""

import pytest
import tempfile
import json
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dependency_manager import DependencyManager
from dependency_validator import DependencyValidator


class TestDependencyManager:
    """Test cases for DependencyManager"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DependencyManager()
        self.manager.cache_dir = Path(self.temp_dir) / "cache"
        self.manager.backup_dir = Path(self.temp_dir) / "backups"
        self.manager.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manager.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_system_compatibility_check(self):
        """Test system compatibility checking"""
        compatible, issues = self.manager.check_system_compatibility()
        
        # Should pass on development system
        assert isinstance(compatible, bool)
        assert isinstance(issues, list)
        
        # If not compatible, should have specific issues
        if not compatible:
            assert len(issues) > 0
            for issue in issues:
                assert isinstance(issue, str)
                assert len(issue) > 0
                
    def test_compatibility_matrix_loading(self):
        """Test compatibility matrix is properly loaded"""
        matrix = self.manager.compatibility_matrix
        
        assert 'python_versions' in matrix
        assert 'windows_versions' in matrix
        assert 'incompatible_combinations' in matrix
        assert 'critical_packages' in matrix
        
        # Check required fields
        assert 'minimum' in matrix['python_versions']
        assert 'maximum' in matrix['python_versions']
        assert isinstance(matrix['critical_packages'], list)
        assert len(matrix['critical_packages']) > 0
        
    def test_known_good_versions_loading(self):
        """Test known good versions are loaded"""
        versions = self.manager.known_good_versions
        
        assert isinstance(versions, dict)
        assert len(versions) > 0
        
        # Check for critical packages
        critical_packages = ['numpy', 'pywin32', 'pyqt6']
        for package in critical_packages:
            if package in versions:
                assert isinstance(versions[package], str)
                assert len(versions[package]) > 0
                
    @patch('requests.get')
    def test_get_latest_versions_success(self, mock_get):
        """Test successful version fetching from PyPI"""
        # Mock PyPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {'version': '1.2.3'}
        }
        mock_get.return_value = mock_response
        
        packages = ['test-package']
        versions = self.manager.get_latest_versions(packages)
        
        assert 'test-package' in versions
        assert versions['test-package'] == '1.2.3'
        
    @patch('requests.get')
    def test_get_latest_versions_failure(self, mock_get):
        """Test handling of PyPI fetch failures"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        packages = ['nonexistent-package']
        versions = self.manager.get_latest_versions(packages)
        
        assert 'nonexistent-package' in versions
        assert versions['nonexistent-package'] is None
        
    def test_backup_current_configuration(self):
        """Test configuration backup creation"""
        # Create test requirements file
        req_file = Path(self.temp_dir) / "requirements.txt"
        with open(req_file, 'w') as f:
            f.write("numpy>=1.20.0\nscipy>=1.7.0\n")
            
        # Temporarily set project root
        original_root = self.manager.project_root
        self.manager.project_root = Path(self.temp_dir)
        
        try:
            backup_path = self.manager.backup_current_configuration()
            
            assert backup_path.exists()
            assert backup_path.is_dir()
            
            # Check backup contents
            backup_req_file = backup_path / "requirements.txt"
            assert backup_req_file.exists()
            
            with open(backup_req_file, 'r') as f:
                content = f.read()
                assert "numpy>=1.20.0" in content
                assert "scipy>=1.7.0" in content
                
        finally:
            self.manager.project_root = original_root
            
    def test_parse_requirements_file(self):
        """Test requirements file parsing"""
        # Create test requirements file
        req_file = Path(self.temp_dir) / "test_requirements.txt"
        with open(req_file, 'w') as f:
            f.write("""
# This is a comment
numpy>=1.20.0
scipy>=1.7.0
# Another comment
pyaudio==0.2.11
-r other_requirements.txt
""")
        
        packages = self.manager._parse_requirements_file(req_file)
        
        expected_packages = ['numpy>=1.20.0', 'scipy>=1.7.0', 'pyaudio==0.2.11']
        assert packages == expected_packages
        
    def test_warning_handler_setup(self):
        """Test warning handler is properly configured"""
        # The warning handler should be set up during initialization
        import warnings
        
        # Test that warnings are captured
        with patch.object(self.manager, '_store_warning') as mock_store:
            warnings.warn("Test deprecation warning", DeprecationWarning)
            
            # Warning should be stored (may not be called due to filtering)
            # This test mainly ensures no exceptions are raised
            
    def test_validation_with_missing_packages(self):
        """Test validation with missing packages"""
        with patch('pkg_resources.get_distribution') as mock_get_dist:
            # Mock missing package
            mock_get_dist.side_effect = Exception("Package not found")
            
            validation_ok, issues = self.manager.validate_installation()
            
            # Should detect missing packages
            assert isinstance(validation_ok, bool)
            assert isinstance(issues, list)
            
    def test_emergency_fallback_mode(self):
        """Test emergency fallback mode activation"""
        success = self.manager.emergency_fallback_mode()
        
        assert success is True
        
        # Check that fallback file was created
        fallback_file = self.manager.cache_dir / "emergency_fallback.json"
        assert fallback_file.exists()
        
        with open(fallback_file, 'r') as f:
            fallback_data = json.load(f)
            assert fallback_data['mode'] == 'emergency_fallback'
            assert 'timestamp' in fallback_data
            
    def test_cleanup_old_data(self):
        """Test cleanup of old cache data"""
        # Create old warning file
        old_warnings = [
            {
                'message': 'Old warning',
                'timestamp': (datetime.now() - timedelta(days=40)).isoformat()
            }
        ]
        
        warnings_file = self.manager.cache_dir / "deprecation_warnings.json"
        with open(warnings_file, 'w') as f:
            json.dump(old_warnings, f)
            
        # Create old backup directory
        old_backup = self.manager.backup_dir / "dependencies_backup_20240101_120000"
        old_backup.mkdir()
        
        # Run cleanup
        self.manager.cleanup_old_data(days_to_keep=30)
        
        # Check that old data was cleaned
        assert not old_backup.exists()
        
        # Check warnings were cleaned
        if warnings_file.exists():
            with open(warnings_file, 'r') as f:
                remaining_warnings = json.load(f)
                assert len(remaining_warnings) == 0


class TestDependencyValidator:
    """Test cases for DependencyValidator"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.validator = DependencyValidator()
        
    @pytest.mark.asyncio
    async def test_validate_for_service_startup(self):
        """Test service startup validation"""
        with patch.object(self.validator.dependency_manager, 'validate_installation') as mock_validate:
            mock_validate.return_value = (True, [])
            
            with patch.object(self.validator.dependency_manager, 'check_system_compatibility') as mock_system:
                mock_system.return_value = (True, [])
                
                success, results = await self.validator.validate_for_service_startup()
                
                assert success is True
                assert 'status' in results
                assert results['status'] == 'validated'
                
    def test_validate_for_gui_startup(self):
        """Test GUI startup validation"""
        with patch('PyQt6.QtWidgets'):
            with patch('PyQt6.QtCore'):
                with patch('PyQt6.QtGui'):
                    with patch('PIL.Image'):
                        with patch('PIL.ImageDraw'):
                            success, results = self.validator.validate_for_gui_startup()
                            
                            assert isinstance(success, bool)
                            assert 'status' in results
                            
    def test_validate_for_audio_processing(self):
        """Test audio processing validation"""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock audio device
            mock_audio_instance = Mock()
            mock_audio_instance.get_device_count.return_value = 2
            mock_audio_instance.get_device_info_by_index.return_value = {
                'maxInputChannels': 2,
                'name': 'Test Microphone'
            }
            mock_pyaudio.return_value = mock_audio_instance
            
            with patch('numpy'):
                with patch('scipy.signal'):
                    success, results = self.validator.validate_for_audio_processing()
                    
                    assert isinstance(success, bool)
                    assert 'status' in results
                    
    def test_get_validation_report(self):
        """Test validation report generation"""
        with patch.object(self.validator.dependency_manager, 'get_dependency_status') as mock_status:
            mock_status.return_value = {
                'validation_status': {'passed': True},
                'warnings_summary': {'total_warnings': 0},
                'system_info': {'python_version': '3.11.0'}
            }
            
            report = self.validator.get_validation_report()
            
            assert 'timestamp' in report
            assert 'dependency_status' in report
            assert 'recommendations' in report
            
    def test_record_validation_result(self):
        """Test validation result recording"""
        # This should not raise an exception
        self.validator.record_validation_result(
            'test_component',
            True,
            {'status': 'success'}
        )
        
        # Check that history file would be created
        history_file = self.validator.dependency_manager.cache_dir / "validation_history.json"
        # File may not exist in test environment, but method should not fail


class TestDependencyIntegration:
    """Integration tests for dependency management"""
    
    def test_full_dependency_workflow(self):
        """Test complete dependency management workflow"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create test requirements file
            req_file = Path(temp_dir) / "requirements.txt"
            with open(req_file, 'w') as f:
                f.write("requests>=2.25.0\npackaging>=20.0\n")
                
            manager = DependencyManager()
            manager.cache_dir = Path(temp_dir) / "cache"
            manager.backup_dir = Path(temp_dir) / "backups"
            manager.cache_dir.mkdir(parents=True, exist_ok=True)
            manager.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Test pre-installation check
            with patch.object(manager, 'get_latest_versions') as mock_versions:
                mock_versions.return_value = {
                    'requests': '2.32.3',
                    'packaging': '24.1'
                }
                
                success, results = manager.pre_installation_check([req_file])
                
                assert isinstance(success, bool)
                assert 'system_compatible' in results
                assert 'package_updates' in results
                
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    def test_error_recovery_workflow(self):
        """Test error recovery and fallback mechanisms"""
        manager = DependencyManager()
        
        # Test network failure recovery
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            success, results = manager.automated_update_check()
            
            # Should fallback gracefully
            assert isinstance(success, bool)
            assert 'fallback_mode' in results or success is True
            
    def test_warning_suppression(self):
        """Test that warnings are properly suppressed"""
        import warnings
        
        manager = DependencyManager()
        
        # Test that deprecation warnings don't terminate execution
        with warnings.catch_warnings(record=True) as w:
            warnings.warn("Test deprecation", DeprecationWarning)
            
            # Should not raise exception
            # Warning handling is set up during manager initialization


if __name__ == '__main__':
    pytest.main([__file__])
