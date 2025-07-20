#!/usr/bin/env python3
"""
VoiceGuard Configuration GUI
Main configuration interface for VoiceGuard settings
"""

import sys
import json
import sqlite3
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
        QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
        QLineEdit, QSlider, QCheckBox, QComboBox, QTextEdit, QProgressBar,
        QGroupBox, QFormLayout, QMessageBox, QDialog, QDialogButtonBox,
        QSpinBox, QTimeEdit, QFileDialog, QSplitter, QHeaderView
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QTime
    from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available - GUI will not work")

from config_manager import ConfigurationManager


class VoiceGuardConfigGUI(QMainWindow):
    """Main configuration GUI for VoiceGuard"""
    
    def __init__(self):
        super().__init__()
        
        if not PYQT_AVAILABLE:
            print("PyQt6 not available - cannot create GUI")
            return
            
        self.config_manager = ConfigurationManager()
        self.logger = logging.getLogger("ConfigGUI")
        
        # Initialize configuration manager
        try:
            self.config_manager.initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {e}")
            
        # Initialize UI
        self.init_ui()
        self.load_configuration()
        
        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("VoiceGuard Configuration")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create status panel
        self.create_status_panel(main_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_voice_commands_tab()
        self.create_audio_settings_tab()
        self.create_ai_config_tab()
        self.create_logs_tab()
        self.create_advanced_tab()
        
        # Create bottom button panel
        self.create_button_panel(main_layout)
        
        # Apply styling
        self.apply_styling()
        
    def create_status_panel(self, parent_layout):
        """Create the status dashboard panel"""
        status_group = QGroupBox("🎤 VoiceGuard Status")
        status_layout = QHBoxLayout(status_group)
        
        # Service status
        service_layout = QVBoxLayout()
        self.service_status_label = QLabel("Service Status: Unknown")
        self.service_status_label.setStyleSheet("font-weight: bold; color: #6C757D;")
        self.helper_status_label = QLabel("Audio Helper: Unknown")
        service_layout.addWidget(self.service_status_label)
        service_layout.addWidget(self.helper_status_label)
        
        # Statistics
        stats_layout = QVBoxLayout()
        self.last_command_label = QLabel("Last Command: Never")
        self.api_keys_label = QLabel("API Keys: 0/30 Active")
        stats_layout.addWidget(self.last_command_label)
        stats_layout.addWidget(self.api_keys_label)
        
        # Test mode indicator
        test_layout = QVBoxLayout()
        self.test_mode_label = QLabel("Test Mode: OFF")
        self.test_mode_button = QPushButton("Toggle Test Mode")
        self.test_mode_button.clicked.connect(self.toggle_test_mode)
        test_layout.addWidget(self.test_mode_label)
        test_layout.addWidget(self.test_mode_button)
        
        status_layout.addLayout(service_layout)
        status_layout.addLayout(stats_layout)
        status_layout.addLayout(test_layout)
        status_layout.addStretch()
        
        parent_layout.addWidget(status_group)
        
    def create_voice_commands_tab(self):
        """Create voice commands configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Commands table
        commands_group = QGroupBox("Voice Commands")
        commands_layout = QVBoxLayout(commands_group)
        
        # Table widget
        self.commands_table = QTableWidget()
        self.commands_table.setColumnCount(5)
        self.commands_table.setHorizontalHeaderLabels([
            "Command", "Enabled", "Confidence", "Last Used", "Actions"
        ])
        
        # Make table headers stretch
        header = self.commands_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        commands_layout.addWidget(self.commands_table)
        
        # Command management buttons
        button_layout = QHBoxLayout()
        
        self.add_command_btn = QPushButton("➕ Add Command")
        self.add_command_btn.clicked.connect(self.add_voice_command)
        
        self.edit_command_btn = QPushButton("✏️ Edit Command")
        self.edit_command_btn.clicked.connect(self.edit_voice_command)
        
        self.delete_command_btn = QPushButton("🗑️ Delete Command")
        self.delete_command_btn.clicked.connect(self.delete_voice_command)
        
        self.test_command_btn = QPushButton("🧪 Test Command")
        self.test_command_btn.clicked.connect(self.test_voice_command)
        
        button_layout.addWidget(self.add_command_btn)
        button_layout.addWidget(self.edit_command_btn)
        button_layout.addWidget(self.delete_command_btn)
        button_layout.addWidget(self.test_command_btn)
        button_layout.addStretch()
        
        commands_layout.addLayout(button_layout)
        layout.addWidget(commands_group)
        
        # Import/Export section
        io_group = QGroupBox("Import/Export")
        io_layout = QHBoxLayout(io_group)
        
        self.import_btn = QPushButton("📥 Import Commands")
        self.import_btn.clicked.connect(self.import_commands)
        
        self.export_btn = QPushButton("📤 Export Commands")
        self.export_btn.clicked.connect(self.export_commands)
        
        self.restore_defaults_btn = QPushButton("🔄 Restore Defaults")
        self.restore_defaults_btn.clicked.connect(self.restore_default_commands)
        
        io_layout.addWidget(self.import_btn)
        io_layout.addWidget(self.export_btn)
        io_layout.addWidget(self.restore_defaults_btn)
        io_layout.addStretch()
        
        layout.addWidget(io_group)
        
        self.tab_widget.addTab(tab, "Voice Commands")
        
    def create_audio_settings_tab(self):
        """Create audio settings configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Microphone settings
        mic_group = QGroupBox("Microphone Settings")
        mic_layout = QFormLayout(mic_group)
        
        # Device selection
        self.mic_device_combo = QComboBox()
        self.refresh_audio_devices()
        mic_layout.addRow("Microphone Device:", self.mic_device_combo)
        
        # Test audio button
        self.test_audio_btn = QPushButton("🎤 Test Audio")
        self.test_audio_btn.clicked.connect(self.test_audio)
        mic_layout.addRow("", self.test_audio_btn)
        
        # Sensitivity slider
        sensitivity_layout = QVBoxLayout()
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 100)
        self.sensitivity_slider.setValue(80)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity_label)
        
        self.sensitivity_label = QLabel("Sensitivity: 80%")
        sensitivity_layout.addWidget(self.sensitivity_label)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        
        mic_layout.addRow("Microphone Sensitivity:", sensitivity_layout)
        
        # Audio level meter
        self.audio_level_bar = QProgressBar()
        self.audio_level_bar.setRange(0, 100)
        self.audio_level_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #28A745;
                border-radius: 3px;
            }
        """)
        mic_layout.addRow("Real-time Audio Level:", self.audio_level_bar)
        
        layout.addWidget(mic_group)
        
        # Recognition settings
        recognition_group = QGroupBox("Recognition Settings")
        recognition_layout = QFormLayout(recognition_group)
        
        # Confidence threshold
        confidence_layout = QVBoxLayout()
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(10, 100)
        self.confidence_slider.setValue(60)
        self.confidence_slider.valueChanged.connect(self.update_confidence_label)
        
        self.confidence_label = QLabel("Confidence Threshold: 60%")
        confidence_layout.addWidget(self.confidence_label)
        confidence_layout.addWidget(self.confidence_slider)
        
        help_label = QLabel("Lower = More Sensitive (may trigger false positives)\n"
                           "Higher = Less Sensitive (may miss quiet commands)")
        help_label.setStyleSheet("color: #6C757D; font-size: 10px;")
        confidence_layout.addWidget(help_label)
        
        recognition_layout.addRow("Recognition Confidence:", confidence_layout)
        
        # Processing options
        self.noise_suppression_cb = QCheckBox("Enable Noise Suppression")
        self.noise_suppression_cb.setChecked(True)
        recognition_layout.addRow("", self.noise_suppression_cb)
        
        self.voice_activity_cb = QCheckBox("Voice Activity Detection")
        self.voice_activity_cb.setChecked(True)
        recognition_layout.addRow("", self.voice_activity_cb)
        
        self.push_to_talk_cb = QCheckBox("Push-to-Talk Mode (Ctrl+Space)")
        recognition_layout.addRow("", self.push_to_talk_cb)
        
        layout.addWidget(recognition_group)
        
        self.tab_widget.addTab(tab, "Audio Settings")
        
    def load_configuration(self):
        """Load configuration from database"""
        try:
            # Load voice commands
            self.load_voice_commands()
            
            # Load settings
            self.load_settings()
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            QMessageBox.warning(self, "Configuration Error", 
                              f"Failed to load configuration: {e}")
            
    def load_voice_commands(self):
        """Load voice commands into table"""
        try:
            commands = self.config_manager.get_voice_commands()
            
            self.commands_table.setRowCount(len(commands))
            
            for row, command in enumerate(commands):
                # Command text
                self.commands_table.setItem(row, 0, QTableWidgetItem(command['command_text']))
                
                # Enabled checkbox
                enabled_item = QTableWidgetItem()
                enabled_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                enabled_item.setCheckState(Qt.CheckState.Checked if command['enabled'] else Qt.CheckState.Unchecked)
                self.commands_table.setItem(row, 1, enabled_item)
                
                # Confidence threshold
                confidence_item = QTableWidgetItem(f"{command['confidence_threshold']:.1f}")
                self.commands_table.setItem(row, 2, confidence_item)
                
                # Last used (placeholder)
                self.commands_table.setItem(row, 3, QTableWidgetItem("Never"))
                
                # Actions (placeholder)
                self.commands_table.setItem(row, 4, QTableWidgetItem("Edit | Delete"))
                
        except Exception as e:
            self.logger.error(f"Failed to load voice commands: {e}")
            
    def load_settings(self):
        """Load settings from configuration"""
        try:
            # Audio settings
            sensitivity = self.config_manager.get_setting("microphone_sensitivity", 0.8)
            self.sensitivity_slider.setValue(int(sensitivity * 100))
            
            confidence = self.config_manager.get_setting("confidence_threshold", 0.6)
            self.confidence_slider.setValue(int(confidence * 100))
            
            # Checkboxes
            self.noise_suppression_cb.setChecked(
                self.config_manager.get_setting("noise_suppression", True)
            )
            self.voice_activity_cb.setChecked(
                self.config_manager.get_setting("voice_activity_detection", True)
            )
            
            # Test mode
            test_mode = self.config_manager.get_setting("test_mode", False)
            self.test_mode_label.setText(f"Test Mode: {'ON' if test_mode else 'OFF'}")
            
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            
    def apply_styling(self):
        """Apply custom styling to the GUI"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        
    # Placeholder methods for functionality
    def refresh_status(self):
        """Refresh system status"""
        pass
        
    def toggle_test_mode(self):
        """Toggle test mode"""
        current = self.config_manager.get_setting("test_mode", False)
        new_value = not current
        self.config_manager.set_setting("test_mode", new_value)
        self.test_mode_label.setText(f"Test Mode: {'ON' if new_value else 'OFF'}")
        
    def refresh_audio_devices(self):
        """Refresh audio device list"""
        try:
            import pyaudio
            audio = pyaudio.PyAudio()
            
            self.mic_device_combo.clear()
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    self.mic_device_combo.addItem(device_info['name'], i)
                    
            audio.terminate()
        except Exception as e:
            self.logger.error(f"Failed to refresh audio devices: {e}")
            
    def update_sensitivity_label(self, value):
        """Update sensitivity label"""
        self.sensitivity_label.setText(f"Sensitivity: {value}%")
        
    def update_confidence_label(self, value):
        """Update confidence label"""
        self.confidence_label.setText(f"Confidence Threshold: {value}%")
        
    # Placeholder methods for button actions
    def add_voice_command(self):
        """Add new voice command"""
        QMessageBox.information(self, "Add Command", "Add command functionality not yet implemented")
        
    def edit_voice_command(self):
        """Edit selected voice command"""
        QMessageBox.information(self, "Edit Command", "Edit command functionality not yet implemented")
        
    def delete_voice_command(self):
        """Delete selected voice command"""
        QMessageBox.information(self, "Delete Command", "Delete command functionality not yet implemented")
        
    def test_voice_command(self):
        """Test voice command recognition"""
        QMessageBox.information(self, "Test Command", "Test command functionality not yet implemented")
        
    def test_audio(self):
        """Test audio input"""
        QMessageBox.information(self, "Test Audio", "Audio test functionality not yet implemented")
        
    def import_commands(self):
        """Import voice commands from file"""
        QMessageBox.information(self, "Import", "Import functionality not yet implemented")
        
    def export_commands(self):
        """Export voice commands to file"""
        QMessageBox.information(self, "Export", "Export functionality not yet implemented")
        
    def restore_default_commands(self):
        """Restore default voice commands"""
        QMessageBox.information(self, "Restore Defaults", "Restore defaults functionality not yet implemented")
        
    def create_ai_config_tab(self):
        """Create AI configuration tab (placeholder)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("AI Configuration tab - To be implemented"))
        self.tab_widget.addTab(tab, "AI Configuration")
        
    def create_logs_tab(self):
        """Create logs tab (placeholder)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Logs tab - To be implemented"))
        self.tab_widget.addTab(tab, "Logs")
        
    def create_advanced_tab(self):
        """Create advanced settings tab (placeholder)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Advanced settings tab - To be implemented"))
        self.tab_widget.addTab(tab, "Advanced")
        
    def create_button_panel(self, parent_layout):
        """Create bottom button panel"""
        button_layout = QHBoxLayout()
        
        # Apply changes
        self.apply_btn = QPushButton("✅ Apply Changes")
        self.apply_btn.clicked.connect(self.apply_changes)
        
        # Help button
        self.help_btn = QPushButton("❓ Help")
        self.help_btn.clicked.connect(self.show_help)
        
        # Standard buttons
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_changes)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.help_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        parent_layout.addLayout(button_layout)
        
    def apply_changes(self):
        """Apply configuration changes"""
        QMessageBox.information(self, "Apply Changes", "Apply changes functionality not yet implemented")
        
    def accept_changes(self):
        """Accept changes and close"""
        self.apply_changes()
        self.close()
        
    def show_help(self):
        """Show help documentation"""
        QMessageBox.information(self, "Help", "Help functionality not yet implemented")
