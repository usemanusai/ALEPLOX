#!/usr/bin/env python3
"""
VoiceGuard Dependency Validator
Integration points for dependency management across VoiceGuard components
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json

from dependency_manager import DependencyManager


class DependencyValidator:
    """Dependency validation integration for VoiceGuard components"""
    
    def __init__(self):
        self.logger = logging.getLogger("DependencyValidator")
        self.dependency_manager = DependencyManager()
        self.validation_cache = {}
        self.last_validation_time = None
        
    async def validate_for_service_startup(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate dependencies before service startup"""
        self.logger.info("Validating dependencies for service startup...")
        
        try:
            # Quick validation check
            validation_ok, issues = self.dependency_manager.validate_installation()
            
            if not validation_ok:
                self.logger.error(f"Dependency validation failed: {issues}")
                
                # Try emergency fallback mode
                fallback_ok = self.dependency_manager.emergency_fallback_mode()
                if fallback_ok:
                    self.logger.warning("Service starting in emergency fallback mode")
                    return True, {
                        'status': 'fallback_mode',
                        'issues': issues,
                        'fallback_enabled': True
                    }
                else:
                    return False, {
                        'status': 'failed',
                        'issues': issues,
                        'fallback_enabled': False
                    }
                    
            # Full system check
            system_ok, system_issues = self.dependency_manager.check_system_compatibility()
            
            if not system_ok:
                self.logger.warning(f"System compatibility issues: {system_issues}")
                
            # Automated update check (non-blocking)
            asyncio.create_task(self._background_update_check())
            
            return True, {
                'status': 'validated',
                'validation_issues': issues,
                'system_issues': system_issues,
                'fallback_enabled': False
            }
            
        except Exception as e:
            self.logger.error(f"Dependency validation error: {e}")
            
            # Emergency fallback
            fallback_ok = self.dependency_manager.emergency_fallback_mode()
            return fallback_ok, {
                'status': 'error',
                'error': str(e),
                'fallback_enabled': fallback_ok
            }
            
    async def _background_update_check(self):
        """Background update check (non-blocking)"""
        try:
            self.logger.debug("Running background dependency update check...")
            success, results = self.dependency_manager.automated_update_check()
            
            if not success:
                self.logger.warning("Background update check found issues")
                
            # Log results for monitoring
            if results.get('package_updates'):
                update_count = len(results['package_updates'])
                self.logger.info(f"Background check found {update_count} package updates available")
                
        except Exception as e:
            self.logger.debug(f"Background update check failed: {e}")
            
    def validate_for_gui_startup(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate dependencies for GUI startup"""
        self.logger.info("Validating dependencies for GUI startup...")
        
        try:
            # Check GUI-specific dependencies
            gui_packages = ['PyQt6', 'pillow']
            gui_issues = []
            
            for package in gui_packages:
                try:
                    if package == 'PyQt6':
                        import PyQt6.QtWidgets
                        import PyQt6.QtCore
                        import PyQt6.QtGui
                    elif package == 'pillow':
                        from PIL import Image, ImageDraw
                        
                except ImportError as e:
                    gui_issues.append(f"GUI dependency {package} import failed: {e}")
                    
            if gui_issues:
                return False, {
                    'status': 'gui_dependencies_failed',
                    'issues': gui_issues
                }
                
            # General validation
            validation_ok, issues = self.dependency_manager.validate_installation()
            
            return validation_ok, {
                'status': 'validated' if validation_ok else 'issues_found',
                'issues': issues,
                'gui_specific_issues': gui_issues
            }
            
        except Exception as e:
            self.logger.error(f"GUI dependency validation error: {e}")
            return False, {
                'status': 'error',
                'error': str(e)
            }
            
    def validate_for_audio_processing(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate dependencies for audio processing"""
        self.logger.info("Validating dependencies for audio processing...")
        
        try:
            # Check audio-specific dependencies
            audio_packages = {
                'pyaudio': 'PyAudio',
                'numpy': 'numpy',
                'scipy': 'scipy.signal',
                'librosa': 'librosa',
                'webrtcvad': 'webrtcvad'
            }
            
            audio_issues = []
            
            for package, import_name in audio_packages.items():
                try:
                    __import__(import_name)
                except ImportError as e:
                    audio_issues.append(f"Audio dependency {package} import failed: {e}")
                    
            # Test PyAudio specifically
            try:
                import pyaudio
                audio = pyaudio.PyAudio()
                
                # Check for available input devices
                input_devices = []
                for i in range(audio.get_device_count()):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        input_devices.append(device_info)
                        
                audio.terminate()
                
                if not input_devices:
                    audio_issues.append("No audio input devices found")
                    
            except Exception as e:
                audio_issues.append(f"PyAudio device check failed: {e}")
                
            if audio_issues:
                return False, {
                    'status': 'audio_dependencies_failed',
                    'issues': audio_issues
                }
                
            return True, {
                'status': 'validated',
                'audio_devices_found': len(input_devices) if 'input_devices' in locals() else 0
            }
            
        except Exception as e:
            self.logger.error(f"Audio dependency validation error: {e}")
            return False, {
                'status': 'error',
                'error': str(e)
            }
            
    def validate_for_installation(self, requirements_files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
        """Validate dependencies before installation"""
        self.logger.info("Running pre-installation dependency validation...")
        
        try:
            # Run comprehensive pre-installation check
            success, results = self.dependency_manager.pre_installation_check(requirements_files)
            
            if not success:
                self.logger.error("Pre-installation validation failed")
                return False, results
                
            # Check for recommended updates
            if results.get('package_updates'):
                update_count = len(results['package_updates'])
                self.logger.info(f"Found {update_count} package updates available")
                
                # Optionally auto-update (with backup)
                if self._should_auto_update():
                    backup_path = self.dependency_manager.backup_current_configuration()
                    
                    updates = {
                        pkg: info['latest'] 
                        for pkg, info in results['package_updates'].items()
                        if info['latest']
                    }
                    
                    update_success = self.dependency_manager.update_requirements_files(
                        updates, backup_path
                    )
                    
                    if update_success:
                        self.logger.info("Requirements files updated with latest versions")
                        results['auto_updated'] = True
                        results['backup_path'] = str(backup_path)
                    else:
                        self.logger.warning("Auto-update failed, proceeding with current versions")
                        
            return True, results
            
        except Exception as e:
            self.logger.error(f"Installation validation error: {e}")
            return False, {
                'status': 'error',
                'error': str(e)
            }
            
    def _should_auto_update(self) -> bool:
        """Determine if auto-update should be performed"""
        # For now, be conservative and don't auto-update
        # This could be made configurable
        return False
        
    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report"""
        try:
            # Get dependency status
            status = self.dependency_manager.get_dependency_status()
            
            # Add validation-specific information
            report = {
                'timestamp': datetime.now().isoformat(),
                'dependency_status': status,
                'validation_history': self._get_validation_history(),
                'recommendations': self._get_validation_recommendations(status)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating validation report: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'report_generation_failed'
            }
            
    def _get_validation_history(self) -> List[Dict[str, Any]]:
        """Get recent validation history"""
        history_file = self.dependency_manager.cache_dir / "validation_history.json"
        
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    
                # Return last 10 validations
                return history[-10:] if len(history) > 10 else history
                
        except Exception as e:
            self.logger.debug(f"Could not load validation history: {e}")
            
        return []
        
    def _get_validation_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """Generate validation-specific recommendations"""
        recommendations = []
        
        # Check validation status
        if not status.get('validation_status', {}).get('passed', True):
            recommendations.append("Resolve package validation issues before production use")
            
        # Check for warnings
        warnings_summary = status.get('warnings_summary', {})
        if warnings_summary.get('recent_warnings', 0) > 10:
            recommendations.append("High number of recent deprecation warnings - review and update packages")
            
        # Check system compatibility
        system_info = status.get('system_info', {})
        python_version = system_info.get('python_version', '')
        
        if python_version and python_version < '3.11.0':
            recommendations.append("Consider upgrading to Python 3.11+ for better performance and security")
            
        # Check for critical package updates
        installed_packages = status.get('installed_packages', {})
        critical_packages = self.dependency_manager.compatibility_matrix['critical_packages']
        
        for package in critical_packages:
            if package in installed_packages:
                current_version = installed_packages[package]
                known_good = self.dependency_manager.known_good_versions.get(package)
                
                if known_good and current_version < known_good:
                    recommendations.append(f"Update {package} from {current_version} to {known_good}")
                    
        return recommendations
        
    def record_validation_result(self, component: str, success: bool, details: Dict[str, Any]):
        """Record validation result for history tracking"""
        try:
            history_file = self.dependency_manager.cache_dir / "validation_history.json"
            
            validation_record = {
                'timestamp': datetime.now().isoformat(),
                'component': component,
                'success': success,
                'details': details
            }
            
            # Load existing history
            history = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    
            # Add new record
            history.append(validation_record)
            
            # Keep only last 100 records
            if len(history) > 100:
                history = history[-100:]
                
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.debug(f"Could not record validation result: {e}")


# Global validator instance
dependency_validator = DependencyValidator()
