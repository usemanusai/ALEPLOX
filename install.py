#!/usr/bin/env python3
"""
VoiceGuard Installation Script
Handles service installation, configuration, and setup
"""

import sys
import os
import subprocess
import shutil
import json
import winreg
from pathlib import Path
import win32serviceutil
import win32service
import win32security
import ntsecuritycon
import logging


class VoiceGuardInstaller:
    """VoiceGuard installation and setup manager"""
    
    def __init__(self):
        self.install_dir = Path("C:/Program Files/VoiceGuard")
        self.data_dir = Path("C:/ProgramData/VoiceGuard")
        self.service_name = "VoiceGuardService"
        self.logger = self.setup_logging()
        
    def setup_logging(self):
        """Setup installation logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger("VoiceGuardInstaller")
        
    def install(self):
        """Complete installation process"""
        print("🎤 VoiceGuard Emergency Shutdown Service Installer")
        print("=" * 50)
        
        try:
            # Check if running as administrator
            if not self.is_admin():
                print("❌ This installer must be run as Administrator")
                print("Please right-click and select 'Run as administrator'")
                return False
                
            # Check prerequisites
            if not self.check_prerequisites():
                return False
                
            # Create directories
            self.create_directories()
            
            # Copy files
            self.copy_files()
            
            # Install Windows Service
            self.install_service()
            
            # Configure permissions
            self.configure_permissions()
            
            # Setup startup items
            self.setup_startup()
            
            # Create shortcuts
            self.create_shortcuts()
            
            print("\n✅ Installation completed successfully!")
            print("\nNext steps:")
            print("1. Run VoiceGuard Configuration to set up voice commands")
            print("2. Configure your microphone permissions in Windows Settings")
            print("3. Add your OpenRouter.ai API keys")
            print("4. Test the system in Test Mode")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Installation failed: {e}")
            self.cleanup_failed_install()
            return False
            
    def is_admin(self):
        """Check if running with administrator privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
            
    def check_prerequisites(self):
        """Check system prerequisites"""
        print("Checking prerequisites...")
        
        # Check Windows version
        import platform
        if not platform.system() == "Windows":
            print("❌ VoiceGuard requires Windows")
            return False
            
        # Check Python version
        if sys.version_info < (3, 11):
            print(f"❌ Python 3.11 or higher required (found {sys.version_info.major}.{sys.version_info.minor})")
            return False
            
        # Check required packages
        required_packages = [
            'pyaudio', 'numpy', 'scipy', 'aiohttp', 'pywin32', 'PyQt6'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
                
        if missing_packages:
            print(f"Installing missing packages: {', '.join(missing_packages)}")
            try:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install'
                ] + missing_packages)
                print("✅ Missing packages installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install packages: {e}")
                return False
                
        print("✅ Prerequisites check passed")
        return True
        
    def create_directories(self):
        """Create installation directories"""
        print("Creating directories...")
        
        directories = [
            self.install_dir,
            self.data_dir,
            self.data_dir / "logs",
            self.data_dir / "config",
            self.data_dir / "backups"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created directory: {directory}")
            
        print("✅ Directories created")
        
    def copy_files(self):
        """Copy application files"""
        print("Copying application files...")
        
        # Source files (current directory)
        source_dir = Path(__file__).parent / "src"
        
        if not source_dir.exists():
            source_dir = Path(__file__).parent
            
        # Python files to copy
        python_files = [
            "main_service.py",
            "main_helper.py", 
            "main_config.py",
            "voiceguard_service.py",
            "audio_helper.py",
            "config_gui.py",
            "config_manager.py",
            "ipc_communication.py",
            "system_tray.py",
            "audio_processor.py",
            "openrouter_client.py",
            "windows_speech.py",
            "keyword_matcher.py",
            "watchdog_system.py",
            "event_logger.py"
        ]
        
        copied_files = 0
        for file_name in python_files:
            source_file = source_dir / file_name
            if source_file.exists():
                shutil.copy2(source_file, self.install_dir / file_name)
                copied_files += 1
                self.logger.info(f"Copied: {file_name}")
            else:
                self.logger.warning(f"Source file not found: {file_name}")
                
        # Create executable wrappers
        self.create_executables()
        
        print(f"✅ {copied_files} files copied")
        
    def create_executables(self):
        """Create executable wrappers"""
        # Service executable
        service_script = f'''@echo off
cd /d "{self.install_dir}"
python main_service.py %*
'''
        with open(self.install_dir / "VoiceGuardService.bat", "w") as f:
            f.write(service_script)
            
        # Helper executable
        helper_script = f'''@echo off
cd /d "{self.install_dir}"
python main_helper.py %*
'''
        with open(self.install_dir / "VoiceGuardHelper.bat", "w") as f:
            f.write(helper_script)
            
        # Config executable
        config_script = f'''@echo off
cd /d "{self.install_dir}"
python main_config.py %*
'''
        with open(self.install_dir / "VoiceGuardConfig.bat", "w") as f:
            f.write(config_script)
            
        self.logger.info("Created executable wrappers")
        
    def install_service(self):
        """Install Windows Service"""
        print("Installing Windows Service...")
        
        try:
            # Change to install directory
            os.chdir(self.install_dir)
            
            # Install service using the main_service.py script
            result = subprocess.run([
                sys.executable, "main_service.py", "install"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Windows Service installed")
                self.logger.info("Service installed successfully")
            else:
                raise Exception(f"Service installation failed: {result.stderr}")
                
            # Configure service recovery
            self.configure_service_recovery()
            
        except Exception as e:
            raise Exception(f"Service installation failed: {e}")
            
    def configure_service_recovery(self):
        """Configure service recovery options"""
        try:
            # Use sc command to configure recovery
            subprocess.run([
                'sc', 'failure', self.service_name,
                'reset=900',  # Reset failure count after 15 minutes
                'actions=restart/60000/restart/60000/reboot/300000'  # Restart after 1min, 1min, reboot after 5min
            ], check=True, capture_output=True)
            
            self.logger.info("Service recovery configured")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not configure service recovery: {e}")
            
    def configure_permissions(self):
        """Configure file and registry permissions"""
        print("Configuring permissions...")
        
        try:
            # Set permissions on install directory
            subprocess.run([
                'icacls', str(self.install_dir),
                '/grant', 'Users:(RX)',
                '/grant', 'Administrators:(F)',
                '/grant', 'SYSTEM:(F)',
                '/T'
            ], check=False, capture_output=True)
            
            # Set permissions on data directory
            subprocess.run([
                'icacls', str(self.data_dir),
                '/grant', 'Users:(M)',
                '/grant', 'Administrators:(F)',
                '/grant', 'SYSTEM:(F)',
                '/T'
            ], check=False, capture_output=True)
            
            print("✅ Permissions configured")
            
        except Exception as e:
            self.logger.warning(f"Permission configuration warning: {e}")
            
    def setup_startup(self):
        """Setup startup items"""
        print("Configuring startup items...")
        
        # Add helper to startup registry
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            winreg.SetValueEx(
                key,
                "VoiceGuardHelper",
                0,
                winreg.REG_SZ,
                str(self.install_dir / "VoiceGuardHelper.bat")
            )
            
            winreg.CloseKey(key)
            print("✅ Startup configured")
            
        except Exception as e:
            self.logger.warning(f"Could not add to startup: {e}")
            
    def create_shortcuts(self):
        """Create desktop and start menu shortcuts"""
        print("Creating shortcuts...")
        
        try:
            import win32com.client
            
            shell = win32com.client.Dispatch("WScript.Shell")
            
            # Desktop shortcut
            desktop = shell.SpecialFolders("Desktop")
            shortcut = shell.CreateShortCut(os.path.join(desktop, "VoiceGuard Configuration.lnk"))
            shortcut.Targetpath = str(self.install_dir / "VoiceGuardConfig.bat")
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.IconLocation = str(self.install_dir / "VoiceGuardConfig.bat")
            shortcut.save()
            
            # Start menu shortcut
            start_menu = shell.SpecialFolders("StartMenu")
            programs = os.path.join(start_menu, "Programs")
            voiceguard_folder = os.path.join(programs, "VoiceGuard")
            os.makedirs(voiceguard_folder, exist_ok=True)
            
            shortcut = shell.CreateShortCut(os.path.join(voiceguard_folder, "VoiceGuard Configuration.lnk"))
            shortcut.Targetpath = str(self.install_dir / "VoiceGuardConfig.bat")
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.save()
            
            print("✅ Shortcuts created")
            
        except Exception as e:
            self.logger.warning(f"Could not create shortcuts: {e}")
            
    def cleanup_failed_install(self):
        """Cleanup after failed installation"""
        print("Cleaning up failed installation...")
        
        try:
            # Remove service if installed
            try:
                subprocess.run([
                    sys.executable, 
                    str(self.install_dir / "main_service.py"), 
                    "remove"
                ], check=False, capture_output=True)
            except:
                pass
                
            # Remove directories
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir, ignore_errors=True)
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            
    def uninstall(self):
        """Uninstall VoiceGuard"""
        print("🗑️ Uninstalling VoiceGuard...")
        
        try:
            # Stop and remove service
            try:
                subprocess.run([
                    sys.executable,
                    str(self.install_dir / "main_service.py"),
                    "stop"
                ], check=False, capture_output=True)
                
                subprocess.run([
                    sys.executable,
                    str(self.install_dir / "main_service.py"),
                    "remove"
                ], check=False, capture_output=True)
                
                print("✅ Service removed")
            except Exception as e:
                self.logger.warning(f"Service removal warning: {e}")
                
            # Remove startup entry
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(key, "VoiceGuardHelper")
                winreg.CloseKey(key)
            except:
                pass
                
            # Remove directories
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir, ignore_errors=True)
                print("✅ Installation directory removed")
                
            # Keep data directory for user data
            print("ℹ️ User data directory preserved at:", self.data_dir)
            
            print("✅ Uninstallation completed")
            return True
            
        except Exception as e:
            print(f"❌ Uninstallation error: {e}")
            return False


def show_usage():
    """Show usage information"""
    print("""
VoiceGuard Installation Script

Usage:
    python install.py [command]

Commands:
    install     Install VoiceGuard (default)
    uninstall   Uninstall VoiceGuard
    help        Show this help message

Examples:
    python install.py
    python install.py install
    python install.py uninstall
    """)


def main():
    """Main installation entry point"""
    command = sys.argv[1].lower() if len(sys.argv) > 1 else 'install'
    
    if command in ['help', '--help', '-h']:
        show_usage()
        return
        
    installer = VoiceGuardInstaller()
    
    if command == 'uninstall':
        success = installer.uninstall()
    else:  # 'install' or default
        success = installer.install()
        
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
