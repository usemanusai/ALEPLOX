#!/usr/bin/env python3
"""
VoiceGuard Watchdog System
Multi-layer watchdog system for VoiceGuard reliability
"""

import asyncio
import psutil
import win32service
import win32serviceutil
import threading
import logging
import time
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import json

try:
    from dependency_validator import dependency_validator
    DEPENDENCY_VALIDATION_AVAILABLE = True
except ImportError:
    DEPENDENCY_VALIDATION_AVAILABLE = False


class WatchdogManager:
    """Multi-layer watchdog system for VoiceGuard reliability"""
    
    def __init__(self):
        self.is_running = False
        self.logger = logging.getLogger("Watchdog")
        
        # Watchdog layers
        self.service_watchdog = ServiceWatchdog()
        self.process_watchdog = ProcessWatchdog()
        self.system_watchdog = SystemWatchdog()
        self.health_monitor = HealthMonitor()
        self.dependency_watchdog = DependencyWatchdog()
        
        # Recovery manager
        self.recovery_manager = RecoveryManager()
        
        # Status tracking
        self.last_health_check = None
        self.failure_counts = {}
        self.recovery_attempts = {}
        
    def start(self):
        """Start the watchdog system"""
        self.is_running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()
        self.logger.info("Watchdog system started")
        
    def stop(self):
        """Stop the watchdog system"""
        self.is_running = False
        if hasattr(self, 'watchdog_thread'):
            self.watchdog_thread.join(timeout=10)
        self.logger.info("Watchdog system stopped")
        
    def _watchdog_loop(self):
        """Main watchdog monitoring loop"""
        while self.is_running:
            try:
                # Run health checks
                health_status = self._perform_health_checks()
                
                # Process health results
                self._process_health_results(health_status)
                
                # Update last check time
                self.last_health_check = datetime.now(timezone.utc)
                
                # Sleep for check interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Watchdog loop error: {e}")
                time.sleep(60)  # Longer sleep on error
                
    def _perform_health_checks(self) -> Dict[str, Dict]:
        """Perform comprehensive health checks"""
        health_status = {}
        
        try:
            # Service layer health check
            health_status['service'] = self.service_watchdog.check_health()
            
            # Process layer health check
            health_status['process'] = self.process_watchdog.check_health()
            
            # System layer health check
            health_status['system'] = self.system_watchdog.check_health()
            
            # Application health check
            health_status['application'] = self.health_monitor.check_health()

            # Dependency health check
            health_status['dependencies'] = self.dependency_watchdog.check_health()
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            health_status['error'] = {'healthy': False, 'error': str(e)}
            
        return health_status
        
    def _process_health_results(self, health_status: Dict[str, Dict]):
        """Process health check results and trigger recovery if needed"""
        for component, status in health_status.items():
            if not status.get('healthy', False):
                self._handle_component_failure(component, status)
            else:
                # Reset failure count on success
                if component in self.failure_counts:
                    self.failure_counts[component] = 0
                    
    def _handle_component_failure(self, component: str, status: Dict):
        """Handle component failure with escalating recovery"""
        # Increment failure count
        self.failure_counts[component] = self.failure_counts.get(component, 0) + 1
        failure_count = self.failure_counts[component]
        
        self.logger.warning(f"Component {component} failure #{failure_count}: {status}")
        
        # Determine recovery action based on failure count
        if failure_count == 1:
            # First failure - try gentle recovery
            recovery_action = 'restart_component'
        elif failure_count <= 3:
            # Multiple failures - escalate recovery
            recovery_action = 'restart_service'
        else:
            # Persistent failures - system-level recovery
            recovery_action = 'restart_system'
            
        # Execute recovery
        asyncio.create_task(self.recovery_manager.execute_recovery(
            component, recovery_action, status
        ))


class ServiceWatchdog:
    """Windows Service specific watchdog"""
    
    def __init__(self):
        self.logger = logging.getLogger("ServiceWatchdog")
        self.service_name = "VoiceGuardService"
        
    def check_health(self) -> Dict:
        """Check Windows Service health"""
        try:
            # Check service status
            service_status = win32serviceutil.QueryServiceStatus(self.service_name)
            current_state = service_status[1]
            
            if current_state == win32service.SERVICE_RUNNING:
                return {
                    'healthy': True,
                    'status': 'running',
                    'state': current_state
                }
            else:
                return {
                    'healthy': False,
                    'status': 'not_running',
                    'state': current_state,
                    'error': f'Service state: {current_state}'
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }


class ProcessWatchdog:
    """Process-level watchdog monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger("ProcessWatchdog")
        self.monitored_processes = [
            "VoiceGuardService.exe",
            "VoiceGuardHelper.exe"
        ]
        
    def check_health(self) -> Dict:
        """Check process health"""
        try:
            process_status = {}
            
            for process_name in self.monitored_processes:
                processes = [p for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']) 
                           if p.info['name'] == process_name]
                
                if processes:
                    process = processes[0]
                    
                    # Check CPU usage
                    cpu_percent = process.info['cpu_percent']
                    memory_mb = process.info['memory_info'].rss / 1024 / 1024
                    
                    # Health thresholds
                    cpu_healthy = cpu_percent < 50  # Less than 50% CPU
                    memory_healthy = memory_mb < 1024  # Less than 1GB memory
                    
                    process_status[process_name] = {
                        'running': True,
                        'pid': process.info['pid'],
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb,
                        'cpu_healthy': cpu_healthy,
                        'memory_healthy': memory_healthy,
                        'healthy': cpu_healthy and memory_healthy
                    }
                else:
                    process_status[process_name] = {
                        'running': False,
                        'healthy': False,
                        'error': 'Process not found'
                    }
                    
            # Overall health
            all_healthy = all(status.get('healthy', False) for status in process_status.values())
            
            return {
                'healthy': all_healthy,
                'processes': process_status
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }


class SystemWatchdog:
    """System-level health monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger("SystemWatchdog")
        
    def check_health(self) -> Dict:
        """Check system health"""
        try:
            # System resource checks
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('C:')
            
            # Health thresholds
            cpu_healthy = cpu_percent < 80
            memory_healthy = memory.percent < 85
            disk_healthy = disk.percent < 90
            
            # Check microphone availability
            microphone_healthy = self._check_microphone_access()
            
            # Check network connectivity
            network_healthy = self._check_network_connectivity()
            
            overall_healthy = all([
                cpu_healthy, memory_healthy, disk_healthy,
                microphone_healthy, network_healthy
            ])
            
            return {
                'healthy': overall_healthy,
                'cpu_percent': cpu_percent,
                'cpu_healthy': cpu_healthy,
                'memory_percent': memory.percent,
                'memory_healthy': memory_healthy,
                'disk_percent': disk.percent,
                'disk_healthy': disk_healthy,
                'microphone_healthy': microphone_healthy,
                'network_healthy': network_healthy
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
            
    def _check_microphone_access(self) -> bool:
        """Check if microphone is accessible"""
        try:
            import pyaudio
            audio = pyaudio.PyAudio()
            
            # Try to get default input device
            default_device = audio.get_default_input_device_info()
            audio.terminate()
            
            return default_device is not None
            
        except Exception:
            return False
            
    def _check_network_connectivity(self) -> bool:
        """Check network connectivity to OpenRouter.ai"""
        try:
            import socket
            
            # Try to connect to OpenRouter.ai
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('openrouter.ai', 443))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False


class HealthMonitor:
    """Application-specific health monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger("HealthMonitor")
        
    def check_health(self) -> Dict:
        """Check application-specific health"""
        try:
            # Check configuration database
            config_healthy = self._check_config_database()
            
            # Check log files
            logs_healthy = self._check_log_files()
            
            # Check IPC communication
            ipc_healthy = self._check_ipc_communication()
            
            overall_healthy = all([config_healthy, logs_healthy, ipc_healthy])
            
            return {
                'healthy': overall_healthy,
                'config_healthy': config_healthy,
                'logs_healthy': logs_healthy,
                'ipc_healthy': ipc_healthy
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
            
    def _check_config_database(self) -> bool:
        """Check configuration database accessibility"""
        try:
            from pathlib import Path
            import sqlite3
            
            db_path = Path("C:/ProgramData/VoiceGuard/config.db")
            if not db_path.exists():
                return False
                
            # Try to connect and query
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM settings")
                cursor.fetchone()
                
            return True
            
        except Exception:
            return False
            
    def _check_log_files(self) -> bool:
        """Check log file accessibility"""
        try:
            from pathlib import Path
            
            log_dir = Path("C:/ProgramData/VoiceGuard/logs")
            return log_dir.exists() and log_dir.is_dir()
            
        except Exception:
            return False
            
    def _check_ipc_communication(self) -> bool:
        """Check IPC communication health"""
        try:
            import win32file
            
            # Try to check if named pipe exists
            pipe_name = r'\\.\pipe\VoiceGuardIPC'
            
            try:
                handle = win32file.CreateFile(
                    pipe_name,
                    win32file.GENERIC_READ,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                win32file.CloseHandle(handle)
                return True
            except:
                return False
                
        except Exception:
            return False


class RecoveryManager:
    """Manages recovery actions for failed components"""
    
    def __init__(self):
        self.logger = logging.getLogger("RecoveryManager")
        
    async def execute_recovery(self, component: str, action: str, context: Dict):
        """Execute recovery action for failed component"""
        self.logger.info(f"Executing recovery action '{action}' for component '{component}'")
        
        try:
            if action == 'restart_component':
                await self._restart_component(component, context)
            elif action == 'restart_service':
                await self._restart_service()
            elif action == 'restart_system':
                await self._restart_system()
            else:
                self.logger.error(f"Unknown recovery action: {action}")
                
        except Exception as e:
            self.logger.error(f"Recovery action failed: {e}")
            
    async def _restart_component(self, component: str, context: Dict):
        """Restart specific component"""
        if component == 'process':
            # Restart helper process
            subprocess.Popen([
                "C:/Program Files/VoiceGuard/VoiceGuardHelper.exe"
            ])
        elif component == 'service':
            # Restart service
            await self._restart_service()
            
    async def _restart_service(self):
        """Restart VoiceGuard service"""
        try:
            # Stop service
            subprocess.run(['sc', 'stop', 'VoiceGuardService'], 
                         check=False, capture_output=True)
            
            # Wait a moment
            await asyncio.sleep(5)
            
            # Start service
            subprocess.run(['sc', 'start', 'VoiceGuardService'], 
                         check=True, capture_output=True)
            
            self.logger.info("Service restarted successfully")
            
        except Exception as e:
            self.logger.error(f"Service restart failed: {e}")
            
    async def _restart_system(self):
        """Restart the entire system (last resort)"""
        self.logger.critical("Initiating system restart due to persistent failures")
        
        # Log the restart reason
        from pathlib import Path
        log_file = Path("C:/ProgramData/VoiceGuard/logs/emergency_restart.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: Emergency system restart initiated by watchdog\n")
            
        # Restart system
        subprocess.run(['shutdown', '/r', '/t', '60', '/c',
                       'VoiceGuard emergency restart - persistent service failures'],
                      check=False)


class DependencyWatchdog:
    """Dependency health monitoring for watchdog system"""

    def __init__(self):
        self.logger = logging.getLogger("DependencyWatchdog")
        self.last_dependency_check = None
        self.dependency_check_interval = timedelta(hours=6)  # Check every 6 hours

    def check_health(self) -> Dict:
        """Check dependency health status"""
        try:
            current_time = datetime.now(timezone.utc)

            # Skip if checked recently
            if (self.last_dependency_check and
                current_time - self.last_dependency_check < self.dependency_check_interval):
                return {
                    'healthy': True,
                    'status': 'skipped_recent_check',
                    'last_check': self.last_dependency_check.isoformat()
                }

            if not DEPENDENCY_VALIDATION_AVAILABLE:
                return {
                    'healthy': True,
                    'status': 'validation_not_available',
                    'warning': 'Dependency validation module not available'
                }

            # Run dependency validation
            validation_ok, issues = dependency_validator.dependency_manager.validate_installation()

            # Update last check time
            self.last_dependency_check = current_time

            if validation_ok:
                return {
                    'healthy': True,
                    'status': 'validated',
                    'last_check': current_time.isoformat()
                }
            else:
                return {
                    'healthy': False,
                    'status': 'validation_failed',
                    'issues': issues,
                    'last_check': current_time.isoformat()
                }

        except Exception as e:
            self.logger.error(f"Dependency health check error: {e}")
            return {
                'healthy': False,
                'status': 'check_error',
                'error': str(e)
            }
