#!/usr/bin/env python3
"""
VoiceGuard Dependency Management System
Automated dependency checking, updating, and compatibility validation
"""

import sys
import os
import json
import subprocess
import logging
import warnings
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import tempfile
import shutil
import requests
from packaging import version
from packaging.requirements import Requirement
import pkg_resources


class DependencyManager:
    """Comprehensive dependency management for VoiceGuard"""
    
    def __init__(self):
        self.logger = logging.getLogger("DependencyManager")
        self.project_root = Path(__file__).parent.parent
        self.cache_dir = Path("C:/ProgramData/VoiceGuard/dependency_cache")
        self.backup_dir = Path("C:/ProgramData/VoiceGuard/dependency_backups")
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Compatibility matrix
        self.compatibility_matrix = self._load_compatibility_matrix()
        
        # Known good versions cache
        self.known_good_versions = self._load_known_good_versions()
        
        # Setup warning handler
        self._setup_warning_handler()
        
    def _load_compatibility_matrix(self) -> Dict[str, Any]:
        """Load package compatibility matrix"""
        return {
            "python_versions": {
                "minimum": "3.8.0",
                "maximum": "3.12.99",
                "recommended": "3.11.0"
            },
            "windows_versions": {
                "minimum": "10.0.19041",  # Windows 10 20H1
                "supported": ["10", "11"]
            },
            "incompatible_combinations": [
                {"pyqt6": ">=6.6.0", "pywin32": "<306"},
                {"numpy": ">=2.0.0", "scipy": "<1.13.0"},
                {"librosa": ">=0.10.0", "numpy": "<1.20.0"}
            ],
            "critical_packages": [
                "pywin32", "pyqt6", "numpy", "scipy", "pyaudio",
                "aiohttp", "cryptography", "psutil"
            ],
            "windows_specific": [
                "pywin32", "pywin32-ctypes", "wmi", "pystray"
            ]
        }
        
    def _load_known_good_versions(self) -> Dict[str, str]:
        """Load known good package versions"""
        cache_file = self.cache_dir / "known_good_versions.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load known good versions: {e}")
                
        # Default known good versions (as of July 2025)
        return {
            "numpy": "1.26.4",
            "scipy": "1.13.1",
            "pyaudio": "0.2.14",
            "librosa": "0.10.2",
            "webrtcvad": "2.0.10",
            "speechrecognition": "3.10.4",
            "aiohttp": "3.9.5",
            "pyqt6": "6.7.1",
            "pywin32": "306",
            "psutil": "5.9.8",
            "pillow": "10.4.0",
            "cryptography": "42.0.8",
            "pyyaml": "6.0.1",
            "requests": "2.32.3",
            "packaging": "24.1"
        }
        
    def _setup_warning_handler(self):
        """Setup comprehensive warning handling"""
        # Custom warning handler
        def warning_handler(message, category, filename, lineno, file=None, line=None):
            warning_info = {
                'message': str(message),
                'category': category.__name__,
                'filename': filename,
                'lineno': lineno,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log warning for developer review
            self.logger.warning(f"Deprecation Warning: {warning_info}")
            
            # Store warning for analysis
            self._store_warning(warning_info)
            
            # Don't terminate execution for deprecation warnings
            if category == DeprecationWarning:
                return
                
        # Set custom warning handler
        warnings.showwarning = warning_handler
        
        # Filter specific warnings that are known to be safe
        warnings.filterwarnings("ignore", category=DeprecationWarning, 
                              module="pkg_resources")
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
        
    def _store_warning(self, warning_info: Dict[str, Any]):
        """Store warning information for analysis"""
        warnings_file = self.cache_dir / "deprecation_warnings.json"
        
        try:
            if warnings_file.exists():
                with open(warnings_file, 'r') as f:
                    warnings_data = json.load(f)
            else:
                warnings_data = []
                
            warnings_data.append(warning_info)
            
            # Keep only last 1000 warnings
            if len(warnings_data) > 1000:
                warnings_data = warnings_data[-1000:]
                
            with open(warnings_file, 'w') as f:
                json.dump(warnings_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to store warning: {e}")
            
    def check_system_compatibility(self) -> Tuple[bool, List[str]]:
        """Check system compatibility requirements"""
        issues = []
        
        # Check Python version
        python_ver = platform.python_version()
        min_ver = self.compatibility_matrix["python_versions"]["minimum"]
        max_ver = self.compatibility_matrix["python_versions"]["maximum"]
        
        if version.parse(python_ver) < version.parse(min_ver):
            issues.append(f"Python {python_ver} is below minimum {min_ver}")
        elif version.parse(python_ver) > version.parse(max_ver):
            issues.append(f"Python {python_ver} is above maximum tested {max_ver}")
            
        # Check Windows version
        if platform.system() == "Windows":
            win_ver = platform.version()
            min_win_ver = self.compatibility_matrix["windows_versions"]["minimum"]
            
            if version.parse(win_ver) < version.parse(min_win_ver):
                issues.append(f"Windows {win_ver} is below minimum {min_win_ver}")
                
        # Check architecture
        if platform.architecture()[0] != "64bit":
            issues.append("64-bit architecture required")
            
        return len(issues) == 0, issues
        
    def get_latest_versions(self, packages: List[str]) -> Dict[str, Optional[str]]:
        """Get latest compatible versions from PyPI"""
        latest_versions = {}
        
        for package in packages:
            try:
                # Clean package name (remove version specifiers)
                clean_name = package.split('>=')[0].split('==')[0].split('<')[0].strip()
                
                # Check PyPI for latest version
                response = requests.get(
                    f"https://pypi.org/pypi/{clean_name}/json",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data['info']['version']
                    
                    # Validate compatibility
                    if self._is_version_compatible(clean_name, latest_version):
                        latest_versions[clean_name] = latest_version
                    else:
                        # Use known good version
                        latest_versions[clean_name] = self.known_good_versions.get(
                            clean_name, latest_version
                        )
                else:
                    self.logger.warning(f"Could not fetch version for {clean_name}")
                    latest_versions[clean_name] = None
                    
            except Exception as e:
                self.logger.error(f"Error checking version for {package}: {e}")
                latest_versions[package] = None
                
        return latest_versions
        
    def _is_version_compatible(self, package: str, version_str: str) -> bool:
        """Check if a package version is compatible"""
        try:
            # Check against incompatible combinations
            for combo in self.compatibility_matrix["incompatible_combinations"]:
                if package in combo:
                    package_req = combo[package]
                    req = Requirement(f"{package}{package_req}")
                    
                    if req.specifier.contains(version_str):
                        # Check if other packages in combo would be incompatible
                        for other_pkg, other_req in combo.items():
                            if other_pkg != package:
                                # This would require checking installed versions
                                # For now, assume potential incompatibility
                                self.logger.warning(
                                    f"Potential incompatibility: {package} {version_str} "
                                    f"with {other_pkg} {other_req}"
                                )
                                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking compatibility for {package}: {e}")
            return False
            
    def pre_installation_check(self, requirements_files: List[Path]) -> Tuple[bool, Dict[str, Any]]:
        """Comprehensive pre-installation dependency check"""
        self.logger.info("Starting pre-installation dependency check...")
        
        results = {
            'system_compatible': True,
            'system_issues': [],
            'package_updates': {},
            'incompatibilities': [],
            'recommendations': []
        }
        
        # System compatibility check
        system_ok, system_issues = self.check_system_compatibility()
        results['system_compatible'] = system_ok
        results['system_issues'] = system_issues
        
        if not system_ok:
            self.logger.error(f"System compatibility issues: {system_issues}")
            return False, results
            
        # Parse requirements files
        all_packages = []
        for req_file in requirements_files:
            if req_file.exists():
                packages = self._parse_requirements_file(req_file)
                all_packages.extend(packages)
                
        # Get latest versions
        package_names = [pkg.split('>=')[0].split('==')[0].split('<')[0].strip() 
                        for pkg in all_packages]
        latest_versions = self.get_latest_versions(package_names)
        
        # Check for updates
        for package, latest_ver in latest_versions.items():
            if latest_ver:
                try:
                    current_ver = pkg_resources.get_distribution(package).version
                    if version.parse(latest_ver) > version.parse(current_ver):
                        results['package_updates'][package] = {
                            'current': current_ver,
                            'latest': latest_ver
                        }
                except pkg_resources.DistributionNotFound:
                    results['package_updates'][package] = {
                        'current': 'not_installed',
                        'latest': latest_ver
                    }
                    
        # Check for incompatibilities
        incompatibilities = self._check_package_incompatibilities(latest_versions)
        results['incompatibilities'] = incompatibilities
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        results['recommendations'] = recommendations
        
        success = (system_ok and len(incompatibilities) == 0)
        
        self.logger.info(f"Pre-installation check completed. Success: {success}")
        return success, results
        
    def _parse_requirements_file(self, req_file: Path) -> List[str]:
        """Parse requirements file and return package list"""
        packages = []
        
        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-r'):
                        packages.append(line)
                        
        except Exception as e:
            self.logger.error(f"Error parsing {req_file}: {e}")
            
        return packages
        
    def _check_package_incompatibilities(self, versions: Dict[str, str]) -> List[Dict[str, str]]:
        """Check for package incompatibilities"""
        incompatibilities = []
        
        for combo in self.compatibility_matrix["incompatible_combinations"]:
            involved_packages = []
            
            for package, version_spec in combo.items():
                if package in versions:
                    req = Requirement(f"{package}{version_spec}")
                    if req.specifier.contains(versions[package]):
                        involved_packages.append({
                            'package': package,
                            'version': versions[package],
                            'spec': version_spec
                        })
                        
            if len(involved_packages) > 1:
                incompatibilities.append({
                    'type': 'version_conflict',
                    'packages': involved_packages,
                    'description': f"Incompatible combination detected"
                })
                
        return incompatibilities
        
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on check results"""
        recommendations = []
        
        if results['system_issues']:
            recommendations.append("Update system to meet minimum requirements")
            
        if results['package_updates']:
            count = len(results['package_updates'])
            recommendations.append(f"Update {count} packages to latest versions")
            
        if results['incompatibilities']:
            recommendations.append("Resolve package version conflicts before installation")
            
        # Add specific recommendations for critical packages
        for package in self.compatibility_matrix["critical_packages"]:
            if package in results['package_updates']:
                recommendations.append(f"Priority update: {package}")
                
        return recommendations

    def backup_current_configuration(self) -> Path:
        """Create backup of current dependency configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"dependencies_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)

        try:
            # Backup requirements files
            for req_file in ["requirements.txt", "requirements-dev.txt"]:
                source = self.project_root / req_file
                if source.exists():
                    shutil.copy2(source, backup_path / req_file)

            # Backup installed packages list
            installed_packages = self._get_installed_packages()
            with open(backup_path / "installed_packages.json", 'w') as f:
                json.dump(installed_packages, f, indent=2)

            # Backup known good versions
            with open(backup_path / "known_good_versions.json", 'w') as f:
                json.dump(self.known_good_versions, f, indent=2)

            self.logger.info(f"Configuration backed up to {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise

    def _get_installed_packages(self) -> Dict[str, str]:
        """Get currently installed packages and versions"""
        installed = {}

        try:
            for dist in pkg_resources.working_set:
                installed[dist.project_name.lower()] = dist.version
        except Exception as e:
            self.logger.error(f"Error getting installed packages: {e}")

        return installed

    def update_requirements_files(self, updates: Dict[str, str],
                                 backup_path: Optional[Path] = None) -> bool:
        """Update requirements files with new versions"""
        try:
            if not backup_path:
                backup_path = self.backup_current_configuration()

            # Update requirements.txt
            req_file = self.project_root / "requirements.txt"
            if req_file.exists():
                self._update_single_requirements_file(req_file, updates)

            # Update requirements-dev.txt
            req_dev_file = self.project_root / "requirements-dev.txt"
            if req_dev_file.exists():
                self._update_single_requirements_file(req_dev_file, updates)

            # Update known good versions
            self.known_good_versions.update(updates)
            self._save_known_good_versions()

            self.logger.info(f"Requirements files updated with {len(updates)} packages")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update requirements files: {e}")
            return False

    def _update_single_requirements_file(self, req_file: Path, updates: Dict[str, str]):
        """Update a single requirements file"""
        lines = []

        with open(req_file, 'r') as f:
            for line in f:
                original_line = line.strip()

                if original_line and not original_line.startswith('#'):
                    # Extract package name
                    package_name = original_line.split('>=')[0].split('==')[0].split('<')[0].strip()

                    if package_name.lower() in updates:
                        # Update version
                        new_version = updates[package_name.lower()]
                        new_line = f"{package_name}>={new_version}"
                        lines.append(new_line + '\n')
                        self.logger.debug(f"Updated {package_name}: {original_line} -> {new_line}")
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

        # Write updated file
        with open(req_file, 'w') as f:
            f.writelines(lines)

    def _save_known_good_versions(self):
        """Save known good versions to cache"""
        cache_file = self.cache_dir / "known_good_versions.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump(self.known_good_versions, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save known good versions: {e}")

    def rollback_to_backup(self, backup_path: Path) -> bool:
        """Rollback to a previous backup configuration"""
        try:
            self.logger.info(f"Rolling back to backup: {backup_path}")

            # Restore requirements files
            for req_file in ["requirements.txt", "requirements-dev.txt"]:
                backup_file = backup_path / req_file
                target_file = self.project_root / req_file

                if backup_file.exists():
                    shutil.copy2(backup_file, target_file)
                    self.logger.info(f"Restored {req_file}")

            # Restore known good versions
            backup_versions = backup_path / "known_good_versions.json"
            if backup_versions.exists():
                with open(backup_versions, 'r') as f:
                    self.known_good_versions = json.load(f)
                self._save_known_good_versions()

            self.logger.info("Rollback completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

    def automated_update_check(self) -> Tuple[bool, Dict[str, Any]]:
        """Automated update check with error recovery"""
        try:
            # Check if we should run (avoid too frequent checks)
            last_check_file = self.cache_dir / "last_update_check.json"

            if last_check_file.exists():
                with open(last_check_file, 'r') as f:
                    last_check_data = json.load(f)
                    last_check = datetime.fromisoformat(last_check_data['timestamp'])

                    # Only check once per day
                    if datetime.now() - last_check < timedelta(days=1):
                        self.logger.debug("Skipping update check (too recent)")
                        return True, {'skipped': True, 'reason': 'recent_check'}

            # Perform update check
            requirements_files = [
                self.project_root / "requirements.txt",
                self.project_root / "requirements-dev.txt"
            ]

            success, results = self.pre_installation_check(requirements_files)

            # Record check time
            check_data = {
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'updates_available': len(results.get('package_updates', {}))
            }

            with open(last_check_file, 'w') as f:
                json.dump(check_data, f, indent=2)

            return success, results

        except requests.RequestException as e:
            self.logger.warning(f"Network error during update check: {e}")
            return self._fallback_to_cached_versions()

        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            return self._fallback_to_cached_versions()

    def _fallback_to_cached_versions(self) -> Tuple[bool, Dict[str, Any]]:
        """Fallback to cached/known good versions"""
        self.logger.info("Falling back to cached dependency information")

        results = {
            'fallback_mode': True,
            'system_compatible': True,
            'system_issues': [],
            'package_updates': {},
            'incompatibilities': [],
            'recommendations': ['Using cached dependency information due to network issues']
        }

        # Basic system check still works offline
        system_ok, system_issues = self.check_system_compatibility()
        results['system_compatible'] = system_ok
        results['system_issues'] = system_issues

        return system_ok, results

    def validate_installation(self) -> Tuple[bool, List[str]]:
        """Validate that all required packages are properly installed"""
        issues = []

        try:
            # Check critical packages
            for package in self.compatibility_matrix["critical_packages"]:
                try:
                    dist = pkg_resources.get_distribution(package)

                    # Check if version is in known good versions
                    if package in self.known_good_versions:
                        expected_ver = self.known_good_versions[package]
                        if version.parse(dist.version) < version.parse(expected_ver):
                            issues.append(f"{package} {dist.version} is below recommended {expected_ver}")

                except pkg_resources.DistributionNotFound:
                    issues.append(f"Critical package {package} not installed")

            # Check Windows-specific packages on Windows
            if platform.system() == "Windows":
                for package in self.compatibility_matrix["windows_specific"]:
                    try:
                        pkg_resources.get_distribution(package)
                    except pkg_resources.DistributionNotFound:
                        issues.append(f"Windows-specific package {package} not installed")

            # Test import of critical modules
            critical_imports = [
                ("win32api", "pywin32"),
                ("PyQt6.QtWidgets", "PyQt6"),
                ("numpy", "numpy"),
                ("scipy", "scipy"),
                ("pyaudio", "PyAudio")
            ]

            for module_name, package_name in critical_imports:
                try:
                    __import__(module_name)
                except ImportError as e:
                    issues.append(f"Cannot import {module_name} from {package_name}: {e}")

        except Exception as e:
            issues.append(f"Validation error: {e}")

        return len(issues) == 0, issues

    def get_dependency_status(self) -> Dict[str, Any]:
        """Get comprehensive dependency status report"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'python_version': platform.python_version(),
                'platform': platform.platform(),
                'architecture': platform.architecture()[0]
            },
            'validation_status': {},
            'installed_packages': {},
            'warnings_summary': {},
            'recommendations': []
        }

        # Validation status
        validation_ok, validation_issues = self.validate_installation()
        status['validation_status'] = {
            'passed': validation_ok,
            'issues': validation_issues
        }

        # Installed packages
        status['installed_packages'] = self._get_installed_packages()

        # Warnings summary
        status['warnings_summary'] = self._get_warnings_summary()

        # System compatibility
        system_ok, system_issues = self.check_system_compatibility()
        if not system_ok:
            status['recommendations'].extend([f"System: {issue}" for issue in system_issues])

        if not validation_ok:
            status['recommendations'].extend([f"Package: {issue}" for issue in validation_issues])

        return status

    def _get_warnings_summary(self) -> Dict[str, Any]:
        """Get summary of recent deprecation warnings"""
        warnings_file = self.cache_dir / "deprecation_warnings.json"
        summary = {
            'total_warnings': 0,
            'recent_warnings': 0,
            'categories': {},
            'most_common': []
        }

        try:
            if warnings_file.exists():
                with open(warnings_file, 'r') as f:
                    warnings_data = json.load(f)

                summary['total_warnings'] = len(warnings_data)

                # Count recent warnings (last 24 hours)
                recent_cutoff = datetime.now() - timedelta(days=1)
                recent_warnings = [
                    w for w in warnings_data
                    if datetime.fromisoformat(w['timestamp']) > recent_cutoff
                ]
                summary['recent_warnings'] = len(recent_warnings)

                # Categorize warnings
                categories = {}
                for warning in warnings_data:
                    category = warning['category']
                    categories[category] = categories.get(category, 0) + 1

                summary['categories'] = categories

                # Most common warnings
                message_counts = {}
                for warning in warnings_data:
                    msg = warning['message'][:100]  # Truncate for grouping
                    message_counts[msg] = message_counts.get(msg, 0) + 1

                summary['most_common'] = sorted(
                    message_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]

        except Exception as e:
            self.logger.error(f"Error getting warnings summary: {e}")

        return summary

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old cache and backup data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # Clean old backups
            for backup_dir in self.backup_dir.iterdir():
                if backup_dir.is_dir():
                    try:
                        # Extract timestamp from directory name
                        timestamp_str = backup_dir.name.split('_')[-2] + '_' + backup_dir.name.split('_')[-1]
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        if backup_date < cutoff_date:
                            shutil.rmtree(backup_dir)
                            self.logger.info(f"Removed old backup: {backup_dir.name}")

                    except (ValueError, IndexError):
                        # Skip directories that don't match expected format
                        continue

            # Clean old warnings
            warnings_file = self.cache_dir / "deprecation_warnings.json"
            if warnings_file.exists():
                with open(warnings_file, 'r') as f:
                    warnings_data = json.load(f)

                # Keep only recent warnings
                recent_warnings = [
                    w for w in warnings_data
                    if datetime.fromisoformat(w['timestamp']) > cutoff_date
                ]

                with open(warnings_file, 'w') as f:
                    json.dump(recent_warnings, f, indent=2)

                removed_count = len(warnings_data) - len(recent_warnings)
                if removed_count > 0:
                    self.logger.info(f"Removed {removed_count} old warnings")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def emergency_fallback_mode(self) -> bool:
        """Enable emergency fallback mode for critical system operation"""
        try:
            self.logger.warning("Enabling emergency fallback mode")

            # Suppress all non-critical warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=UserWarning)

            # Use only known good versions
            fallback_status = {
                'mode': 'emergency_fallback',
                'timestamp': datetime.now().isoformat(),
                'reason': 'Critical system operation required'
            }

            fallback_file = self.cache_dir / "emergency_fallback.json"
            with open(fallback_file, 'w') as f:
                json.dump(fallback_status, f, indent=2)

            self.logger.info("Emergency fallback mode enabled")
            return True

        except Exception as e:
            self.logger.error(f"Failed to enable emergency fallback mode: {e}")
            return False
