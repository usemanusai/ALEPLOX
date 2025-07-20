#!/usr/bin/env python3
"""
VoiceGuard Emergency Shutdown Service
Main Windows Service implementation for emergency system shutdown
"""

import asyncio
import logging
import json
import sqlite3
import win32service
import win32serviceutil
import win32event
import win32api
import win32con
from pathlib import Path
from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional

from config_manager import ConfigurationManager
from ipc_communication import IPCServer
from watchdog_system import WatchdogManager
from event_logger import EventLogger


class VoiceGuardService(win32serviceutil.ServiceFramework):
    """Main Windows Service for VoiceGuard Emergency Shutdown System"""
    
    _svc_name_ = "VoiceGuardService"
    _svc_display_name_ = "VoiceGuard Emergency Shutdown Service"
    _svc_description_ = "AI-powered voice command emergency system shutdown service"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        self.config_manager = ConfigurationManager()
        self.ipc_server = IPCServer()
        self.watchdog = WatchdogManager()
        self.event_logger = EventLogger()
        
        # Initialize logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure structured logging system"""
        log_path = Path("C:/ProgramData/VoiceGuard/logs")
        log_path.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / "service.log"),
                logging.handlers.RotatingFileHandler(
                    log_path / "service_rotating.log",
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
            ]
        )
        self.logger = logging.getLogger("VoiceGuardService")
        
    def SvcStop(self):
        """Service stop handler"""
        self.logger.info("VoiceGuard Service stopping...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        """Main service execution"""
        self.logger.info("VoiceGuard Service starting...")
        self.is_running = True
        
        try:
            # Initialize components
            self.config_manager.initialize()
            self.ipc_server.start()
            self.watchdog.start()
            
            # Log service start
            self.event_logger.log_security_event(1001, "Service Started")
            
            # Main service loop
            asyncio.run(self.main_service_loop())
            
        except Exception as e:
            self.logger.error(f"Service error: {e}")
            self.event_logger.log_security_event(1002, f"Service Error: {e}")
        finally:
            self.cleanup()
            
    async def main_service_loop(self):
        """Main asynchronous service loop"""
        while self.is_running:
            try:
                # Process IPC messages
                await self.process_ipc_messages()
                
                # Check system health
                await self.perform_health_checks()
                
                # Monitor watchdog status
                await self.check_watchdog_status()
                
                # Sleep for 1 second
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                await asyncio.sleep(5)  # Longer sleep on error
                
    async def process_ipc_messages(self):
        """Process incoming IPC messages from helper process"""
        messages = await self.ipc_server.get_pending_messages()
        
        for message in messages:
            if message.type == "COMMAND_DETECTED":
                await self.handle_shutdown_command(message)
            elif message.type == "STATUS_UPDATE":
                await self.handle_status_update(message)
            elif message.type == "CONFIG_CHANGE":
                await self.handle_config_change(message)
                
    async def handle_shutdown_command(self, message):
        """Handle emergency shutdown command"""
        command_data = message.payload
        
        self.logger.critical(f"Emergency shutdown command detected: {command_data['command']}")
        self.event_logger.log_security_event(2002, 
            f"System Shutdown Initiated - Command: {command_data['command']}, "
            f"Confidence: {command_data['confidence']}")
        
        # Check if in test mode
        if self.config_manager.get_setting("test_mode", False):
            self.logger.info("Test mode active - shutdown cancelled")
            return
            
        # Execute shutdown with safety delay
        await self.execute_emergency_shutdown(command_data)
        
    async def execute_emergency_shutdown(self, command_data):
        """Execute system shutdown with safety mechanisms"""
        try:
            # Safety delay with cancellation option
            delay = self.config_manager.get_setting("confirmation_delay", 3)
            
            for i in range(delay, 0, -1):
                self.logger.warning(f"Emergency shutdown in {i} seconds...")
                
                # Check for cancellation
                if await self.check_shutdown_cancellation():
                    self.logger.info("Emergency shutdown cancelled by user")
                    return
                    
                await asyncio.sleep(1)
            
            # Execute shutdown
            self.logger.critical("Executing emergency system shutdown")
            win32api.ExitWindowsEx(win32con.EWX_SHUTDOWN | win32con.EWX_FORCE, 0)
            
        except Exception as e:
            self.logger.error(f"Shutdown execution failed: {e}")
            
    async def check_shutdown_cancellation(self):
        """Check if shutdown has been cancelled"""
        # This would check for cancellation signals from IPC or registry
        # Implementation would depend on specific cancellation mechanism
        return False
        
    async def handle_status_update(self, message):
        """Handle status update from helper process"""
        status_data = message.payload
        self.logger.debug(f"Status update received: {status_data}")
        
    async def handle_config_change(self, message):
        """Handle configuration change notification"""
        config_data = message.payload
        self.logger.info(f"Configuration changed: {config_data}")
        
        # Reload configuration
        self.config_manager.reload_configuration()
        
    async def perform_health_checks(self):
        """Perform periodic health checks"""
        # This would be implemented to check system health
        pass
        
    async def check_watchdog_status(self):
        """Check watchdog system status"""
        # This would monitor the watchdog system
        pass
        
    def cleanup(self):
        """Cleanup resources on service stop"""
        self.logger.info("Cleaning up service resources...")
        
        if hasattr(self, 'ipc_server'):
            self.ipc_server.stop()
        if hasattr(self, 'watchdog'):
            self.watchdog.stop()
            
        self.event_logger.log_security_event(1002, "Service Stopped")


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(VoiceGuardService)
