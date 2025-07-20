#!/usr/bin/env python3
"""
VoiceGuard System Tray Application
System tray integration for VoiceGuard status monitoring
"""

import sys
import threading
import logging
from pathlib import Path
from datetime import datetime
import subprocess

try:
    from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                                QMessageBox, QWidget)
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QIcon, QPixmap
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available - system tray will not work")

try:
    from PIL import Image, ImageDraw
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class SystemTrayApp(QObject):
    """System tray application for VoiceGuard status"""
    
    # Signals
    status_changed = pyqtSignal(str)
    command_detected = pyqtSignal(str, float)
    
    def __init__(self):
        super().__init__()
        self.app = None
        self.tray_icon = None
        self.current_status = "inactive"
        self.logger = logging.getLogger("SystemTray")
        
        # Status tracking
        self.service_running = False
        self.helper_running = False
        self.last_command_time = None
        self.api_keys_active = 0
        self.test_mode = False
        
        if not PYQT_AVAILABLE:
            self.logger.error("PyQt6 not available - system tray disabled")
            return
            
    def start(self):
        """Start the system tray application"""
        if not PYQT_AVAILABLE:
            return
            
        try:
            # Create QApplication if it doesn't exist
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
            else:
                self.app = QApplication.instance()
                
            # Check if system tray is available
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.logger.error("System tray not available")
                return
                
            # Create system tray icon
            self.create_tray_icon()
            
            # Start status update timer
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.update_status)
            self.status_timer.start(5000)  # Update every 5 seconds
            
            self.logger.info("System tray started")
            
        except Exception as e:
            self.logger.error(f"System tray start error: {e}")
            
    def create_tray_icon(self):
        """Create and configure system tray icon"""
        try:
            # Create tray icon
            self.tray_icon = QSystemTrayIcon()
            
            # Set initial icon
            self.update_tray_icon("inactive")
            
            # Create context menu
            self.create_context_menu()
            
            # Connect signals
            self.tray_icon.activated.connect(self.on_tray_activated)
            
            # Show tray icon
            self.tray_icon.show()
            
        except Exception as e:
            self.logger.error(f"Tray icon creation error: {e}")
            
    def create_context_menu(self):
        """Create context menu for tray icon"""
        try:
            menu = QMenu()
            
            # Status section
            self.status_action = QAction("🎤 VoiceGuard", menu)
            self.status_action.setEnabled(False)
            menu.addAction(self.status_action)
            
            menu.addSeparator()
            
            # Service info
            self.service_status_action = QAction("● Service Status: Unknown", menu)
            self.service_status_action.setEnabled(False)
            menu.addAction(self.service_status_action)
            
            self.last_command_action = QAction("📊 Last Command: Never", menu)
            self.last_command_action.setEnabled(False)
            menu.addAction(self.last_command_action)
            
            self.api_keys_action = QAction("🔑 API Keys: 0/30 active", menu)
            self.api_keys_action.setEnabled(False)
            menu.addAction(self.api_keys_action)
            
            menu.addSeparator()
            
            # Actions
            self.config_action = QAction("⚙️ Open Configuration...", menu)
            self.config_action.triggered.connect(self.open_configuration)
            menu.addAction(self.config_action)
            
            self.test_mode_action = QAction("🧪 Toggle Test Mode", menu)
            self.test_mode_action.triggered.connect(self.toggle_test_mode)
            menu.addAction(self.test_mode_action)
            
            self.logs_action = QAction("📋 View Recent Logs...", menu)
            self.logs_action.triggered.connect(self.view_logs)
            menu.addAction(self.logs_action)
            
            menu.addSeparator()
            
            # Service control
            self.restart_action = QAction("🔄 Restart Service", menu)
            self.restart_action.triggered.connect(self.restart_service)
            menu.addAction(self.restart_action)
            
            self.pause_action = QAction("⏸️ Pause Monitoring", menu)
            self.pause_action.triggered.connect(self.pause_monitoring)
            menu.addAction(self.pause_action)
            
            menu.addSeparator()
            
            # Help and exit
            self.help_action = QAction("❓ Help & Documentation", menu)
            self.help_action.triggered.connect(self.show_help)
            menu.addAction(self.help_action)
            
            self.exit_action = QAction("🚪 Exit VoiceGuard", menu)
            self.exit_action.triggered.connect(self.exit_application)
            menu.addAction(self.exit_action)
            
            self.tray_icon.setContextMenu(menu)
            
        except Exception as e:
            self.logger.error(f"Context menu creation error: {e}")
            
    def update_tray_icon(self, status: str):
        """Update tray icon based on status"""
        try:
            # Create icon based on status
            icon_color = {
                'active': (40, 167, 69),      # Green
                'warning': (255, 193, 7),     # Yellow
                'inactive': (220, 53, 69),    # Red
                'test_mode': (23, 162, 184)   # Blue
            }.get(status, (108, 117, 125))    # Gray default
            
            # Create icon image
            if PIL_AVAILABLE:
                icon_image = self.create_icon_image(icon_color)
                qicon = self.pil_to_qicon(icon_image)
            else:
                # Fallback to simple colored icon
                qicon = self.create_simple_icon(icon_color)
                
            self.tray_icon.setIcon(qicon)
            
            # Update tooltip
            tooltip = {
                'active': 'VoiceGuard Active - Monitoring for commands',
                'warning': 'VoiceGuard Warning - Check configuration',
                'inactive': 'VoiceGuard Inactive - Service not running',
                'test_mode': 'VoiceGuard Test Mode - Commands logged only'
            }.get(status, 'VoiceGuard - Unknown status')
            
            self.tray_icon.setToolTip(tooltip)
            
            self.current_status = status
            
        except Exception as e:
            self.logger.error(f"Tray icon update error: {e}")
            
    def create_icon_image(self, color: tuple) -> Image.Image:
        """Create microphone icon image"""
        if not PIL_AVAILABLE:
            return None
            
        # Create 32x32 icon
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw microphone shape
        # Microphone body (rectangle with rounded corners)
        draw.rounded_rectangle([10, 6, 22, 20], radius=3, fill=color)
        
        # Microphone stand
        draw.rectangle([15, 20, 17, 26], fill=color)
        
        # Microphone base
        draw.ellipse([12, 24, 20, 28], fill=color)
        
        return img
        
    def pil_to_qicon(self, pil_image: Image.Image) -> QIcon:
        """Convert PIL image to QIcon"""
        if not PIL_AVAILABLE or not pil_image:
            return QIcon()
            
        # Convert PIL image to bytes
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='PNG')
        img_bytes = img_buffer.getvalue()
        
        # Create QPixmap from bytes
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        
        return QIcon(pixmap)
        
    def create_simple_icon(self, color: tuple) -> QIcon:
        """Create simple colored icon without PIL"""
        # Create a simple colored square as fallback
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(*color))
        return QIcon(pixmap)
        
    def update_status(self):
        """Update system status and tray icon"""
        try:
            # Check service status (placeholder - would check actual service)
            # In real implementation, this would query the service via IPC
            
            # Update context menu text
            if hasattr(self, 'service_status_action'):
                status_text = "● Service Status: Active" if self.service_running else "● Service Status: Inactive"
                self.service_status_action.setText(status_text)
                
            if hasattr(self, 'last_command_action'):
                if self.last_command_time:
                    time_diff = (datetime.now() - self.last_command_time).total_seconds()
                    if time_diff < 60:
                        time_str = f"{int(time_diff)}s ago"
                    elif time_diff < 3600:
                        time_str = f"{int(time_diff/60)}m ago"
                    else:
                        time_str = f"{int(time_diff/3600)}h ago"
                    self.last_command_action.setText(f"📊 Last Command: {time_str}")
                else:
                    self.last_command_action.setText("📊 Last Command: Never")
                    
            if hasattr(self, 'api_keys_action'):
                self.api_keys_action.setText(f"🔑 API Keys: {self.api_keys_active}/30 active")
                
            # Determine overall status
            if self.test_mode:
                new_status = "test_mode"
            elif self.service_running and self.helper_running:
                new_status = "active"
            elif self.service_running or self.helper_running:
                new_status = "warning"
            else:
                new_status = "inactive"
                
            # Update icon if status changed
            if new_status != self.current_status:
                self.update_tray_icon(new_status)
                
        except Exception as e:
            self.logger.error(f"Status update error: {e}")
            
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_configuration()
            
    def show_notification(self, title: str, message: str, icon_type: str = "info", duration: int = 3000):
        """Show system tray notification"""
        try:
            icon = {
                'info': QSystemTrayIcon.MessageIcon.Information,
                'warning': QSystemTrayIcon.MessageIcon.Warning,
                'critical': QSystemTrayIcon.MessageIcon.Critical
            }.get(icon_type, QSystemTrayIcon.MessageIcon.Information)
            
            self.tray_icon.showMessage(title, message, icon, duration)
            
        except Exception as e:
            self.logger.error(f"Notification error: {e}")
            
    # Context menu action handlers
    def open_configuration(self):
        """Open configuration GUI"""
        try:
            config_exe = Path("C:/Program Files/VoiceGuard/VoiceGuardConfig.exe")
            if config_exe.exists():
                subprocess.Popen([str(config_exe)])
            else:
                # Try Python script
                config_script = Path(__file__).parent / "main_config.py"
                if config_script.exists():
                    subprocess.Popen([sys.executable, str(config_script)])
                else:
                    self.show_notification("Error", "Configuration application not found", "warning")
        except Exception as e:
            self.logger.error(f"Open configuration error: {e}")
            
    def toggle_test_mode(self):
        """Toggle test mode"""
        # This would send IPC message to service to toggle test mode
        self.test_mode = not self.test_mode
        self.show_notification(
            "Test Mode", 
            f"Test mode {'enabled' if self.test_mode else 'disabled'}", 
            "info"
        )
        
    def view_logs(self):
        """Open log viewer"""
        try:
            log_path = Path("C:/ProgramData/VoiceGuard/logs")
            subprocess.Popen(['explorer', str(log_path)])
        except Exception as e:
            self.logger.error(f"View logs error: {e}")
            
    def restart_service(self):
        """Restart VoiceGuard service"""
        try:
            subprocess.run(['sc', 'stop', 'VoiceGuardService'], check=False)
            subprocess.run(['sc', 'start', 'VoiceGuardService'], check=True)
            self.show_notification("Service", "VoiceGuard service restarted", "info")
        except Exception as e:
            self.logger.error(f"Restart service error: {e}")
            self.show_notification("Error", "Failed to restart service", "warning")
            
    def pause_monitoring(self):
        """Pause voice monitoring"""
        # This would send IPC message to pause monitoring
        self.show_notification("Monitoring", "Voice monitoring paused", "warning")
        
    def show_help(self):
        """Show help documentation"""
        try:
            import webbrowser
            webbrowser.open("https://github.com/yourusername/voiceguard/blob/main/README.md")
        except Exception as e:
            self.logger.error(f"Show help error: {e}")
            
    def exit_application(self):
        """Exit the application"""
        if not PYQT_AVAILABLE:
            return
            
        reply = QMessageBox.question(
            None,
            "Exit VoiceGuard",
            "Are you sure you want to exit VoiceGuard?\n\nThis will disable emergency shutdown monitoring.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.app:
                self.app.quit()
                
    def quit(self):
        """Quit the system tray application"""
        if self.tray_icon:
            self.tray_icon.hide()
        if self.app:
            self.app.quit()
