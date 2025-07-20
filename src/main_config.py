#!/usr/bin/env python3
"""
VoiceGuard Configuration GUI
Main configuration application entry point
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    
    # Import VoiceGuard GUI
    from config_gui import VoiceGuardConfigGUI
    PYQT_AVAILABLE = True
    
except ImportError as e:
    PYQT_AVAILABLE = False
    print(f"PyQt6 not available: {e}")
    print("Please install PyQt6: pip install PyQt6")


def setup_gui_environment():
    """Setup GUI environment"""
    # Ensure data directories exist
    data_dir = Path("C:/ProgramData/VoiceGuard")
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = logs_dir / "config_gui.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("ConfigGUI")
    logger.info("VoiceGuard configuration GUI environment initialized")
    
    return logger


def check_service_status():
    """Check if VoiceGuard service is running"""
    try:
        import win32serviceutil
        status = win32serviceutil.QueryServiceStatus("VoiceGuardService")
        return status[1] == 4  # SERVICE_RUNNING
    except Exception:
        return False


def check_prerequisites():
    """Check system prerequisites"""
    logger = logging.getLogger("Prerequisites")
    
    # Check PyQt6
    if not PYQT_AVAILABLE:
        logger.error("PyQt6 not available")
        return False
        
    # Check Windows version
    import platform
    if not platform.system() == "Windows":
        logger.error("VoiceGuard requires Windows")
        return False
        
    # Check Python version
    if sys.version_info < (3, 11):
        logger.error("Python 3.11 or higher required")
        return False
        
    logger.info("Prerequisites check passed")
    return True


def create_application():
    """Create and configure QApplication"""
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceGuard Configuration")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VoiceGuard")
    
    # Set application properties
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    
    return app


def show_service_warning():
    """Show warning if service is not running"""
    reply = QMessageBox.warning(
        None,
        "VoiceGuard Service Not Running",
        "The VoiceGuard service is not currently running.\n\n"
        "Some configuration changes may not take effect until the service is started.\n\n"
        "Would you like to continue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    return reply == QMessageBox.StandardButton.Yes


def show_error_dialog(title, message):
    """Show error dialog"""
    try:
        QMessageBox.critical(None, title, message)
    except:
        print(f"ERROR: {title}\n{message}")


def main():
    """Main entry point for configuration GUI"""
    logger = setup_gui_environment()
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            if PYQT_AVAILABLE:
                app = create_application()
                show_error_dialog(
                    "Prerequisites Not Met",
                    "VoiceGuard Configuration requires:\n"
                    "- Windows 11\n"
                    "- Python 3.11+\n"
                    "- PyQt6\n\n"
                    "Please install missing components and try again."
                )
            else:
                print("Prerequisites not met. Please install PyQt6 and try again.")
            sys.exit(1)
            
        # Create QApplication
        app = create_application()
        
        # Check if system tray is available
        from PyQt6.QtWidgets import QSystemTrayIcon
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            
        # Check service status
        service_running = check_service_status()
        if not service_running:
            logger.warning("VoiceGuard service not running")
            if not show_service_warning():
                sys.exit(0)
        else:
            logger.info("VoiceGuard service is running")
            
        # Create and show main window
        try:
            main_window = VoiceGuardConfigGUI()
            
            if main_window is None:
                raise Exception("Failed to create main window")
                
            main_window.show()
            logger.info("Configuration GUI started successfully")
            
        except Exception as e:
            logger.error(f"Failed to create main window: {e}")
            show_error_dialog(
                "GUI Creation Error",
                f"Failed to create the configuration interface:\n\n{e}\n\n"
                "Please check the logs for more details."
            )
            sys.exit(1)
            
        # Run application
        exit_code = app.exec()
        logger.info(f"Configuration GUI exited with code {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Configuration GUI interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Configuration GUI error: {e}")
        
        # Show error dialog if possible
        if PYQT_AVAILABLE:
            try:
                if 'app' not in locals():
                    app = create_application()
                show_error_dialog(
                    "VoiceGuard Configuration Error",
                    f"An unexpected error occurred:\n\n{e}\n\n"
                    "Please check the logs for more details."
                )
            except:
                pass
        else:
            print(f"FATAL ERROR: {e}")
            
        sys.exit(1)


if __name__ == '__main__':
    main()
