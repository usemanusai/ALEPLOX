#!/usr/bin/env python3
"""
VoiceGuard Emergency Shutdown Service
Main service entry point and Windows Service wrapper
"""

import sys
import os
import logging
import asyncio
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import VoiceGuard components
from voiceguard_service import VoiceGuardService
from config_manager import ConfigurationManager
from event_logger import EventLogger

try:
    from dependency_validator import dependency_validator
    DEPENDENCY_VALIDATION_AVAILABLE = True
except ImportError:
    DEPENDENCY_VALIDATION_AVAILABLE = False


def setup_service_environment():
    """Setup service environment and logging"""
    # Ensure data directories exist
    data_dir = Path("C:/ProgramData/VoiceGuard")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    config_dir = data_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    # Setup logging
    log_file = logs_dir / "service.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("VoiceGuardMain")
    logger.info("VoiceGuard service environment initialized")
    
    return logger


def check_prerequisites():
    """Check system prerequisites"""
    logger = logging.getLogger("Prerequisites")
    
    # Check Windows version
    import platform
    if not platform.system() == "Windows":
        logger.error("VoiceGuard requires Windows")
        return False
        
    # Check Python version
    if sys.version_info < (3, 11):
        logger.error("Python 3.11 or higher required")
        return False
        
    # Check required modules
    required_modules = [
        'pyaudio', 'numpy', 'scipy', 'aiohttp', 'pywin32'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
            
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        return False
        
    logger.info("Prerequisites check passed")
    return True


def install_service():
    """Install the Windows Service"""
    logger = logging.getLogger("ServiceInstaller")
    
    try:
        import win32serviceutil
        
        # Install service
        win32serviceutil.InstallService(
            VoiceGuardService._svc_reg_class_,
            VoiceGuardService._svc_name_,
            VoiceGuardService._svc_display_name_,
            description=VoiceGuardService._svc_description_
        )
        
        logger.info("VoiceGuard service installed successfully")
        
        # Configure service recovery
        import subprocess
        subprocess.run([
            'sc', 'failure', VoiceGuardService._svc_name_,
            'reset=900',  # Reset failure count after 15 minutes
            'actions=restart/60000/restart/60000/reboot/300000'
        ], check=False)
        
        logger.info("Service recovery configured")
        return True
        
    except Exception as e:
        logger.error(f"Service installation failed: {e}")
        return False


def remove_service():
    """Remove the Windows Service"""
    logger = logging.getLogger("ServiceRemover")
    
    try:
        import win32serviceutil
        
        # Stop service if running
        try:
            win32serviceutil.StopService(VoiceGuardService._svc_name_)
            logger.info("Service stopped")
        except:
            pass
            
        # Remove service
        win32serviceutil.RemoveService(VoiceGuardService._svc_name_)
        logger.info("VoiceGuard service removed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Service removal failed: {e}")
        return False


def start_service():
    """Start the Windows Service"""
    logger = logging.getLogger("ServiceStarter")
    
    try:
        import win32serviceutil
        win32serviceutil.StartService(VoiceGuardService._svc_name_)
        logger.info("VoiceGuard service started")
        return True
        
    except Exception as e:
        logger.error(f"Service start failed: {e}")
        return False


def stop_service():
    """Stop the Windows Service"""
    logger = logging.getLogger("ServiceStopper")
    
    try:
        import win32serviceutil
        win32serviceutil.StopService(VoiceGuardService._svc_name_)
        logger.info("VoiceGuard service stopped")
        return True
        
    except Exception as e:
        logger.error(f"Service stop failed: {e}")
        return False


def run_console_mode():
    """Run service in console mode for debugging"""
    logger = logging.getLogger("ConsoleMode")
    logger.info("Starting VoiceGuard in console mode...")

    # Validate dependencies before starting service
    if DEPENDENCY_VALIDATION_AVAILABLE:
        logger.info("Validating dependencies for service startup...")

        try:
            import asyncio

            # Run dependency validation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            validation_ok, validation_results = loop.run_until_complete(
                dependency_validator.validate_for_service_startup()
            )

            if not validation_ok:
                logger.error("Dependency validation failed")
                if validation_results.get('fallback_enabled'):
                    logger.warning("Service starting in emergency fallback mode")
                else:
                    logger.error("Cannot start service - critical dependency issues")
                    sys.exit(1)

            elif validation_results.get('status') == 'fallback_mode':
                logger.warning("Service starting in emergency fallback mode due to dependency issues")

            # Record validation result
            dependency_validator.record_validation_result(
                'service_startup',
                validation_ok,
                validation_results
            )

            loop.close()

        except Exception as e:
            logger.error(f"Dependency validation error: {e}")
            logger.warning("Proceeding without dependency validation")
    else:
        logger.warning("Dependency validation not available")

    # Create service instance
    service = VoiceGuardService([])

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        service.SvcStop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run service
    try:
        service.SvcDoRun()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        service.SvcStop()
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)


def show_usage():
    """Show usage information"""
    print("""
VoiceGuard Emergency Shutdown Service

Usage:
    python main_service.py [command]

Commands:
    install     Install the Windows Service
    remove      Remove the Windows Service
    start       Start the Windows Service
    stop        Stop the Windows Service
    restart     Restart the Windows Service
    console     Run in console mode (for debugging)
    debug       Run in debug console mode with verbose logging
    
    If no command is specified, the service will run in console mode.
    
Examples:
    python main_service.py install
    python main_service.py start
    python main_service.py console
    """)


def main():
    """Main entry point for VoiceGuard service"""
    logger = setup_service_environment()
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
            
        # Parse command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == 'install':
                success = install_service()
                sys.exit(0 if success else 1)
                
            elif command == 'remove':
                success = remove_service()
                sys.exit(0 if success else 1)
                
            elif command == 'start':
                success = start_service()
                sys.exit(0 if success else 1)
                
            elif command == 'stop':
                success = stop_service()
                sys.exit(0 if success else 1)
                
            elif command == 'restart':
                stop_service()
                import time
                time.sleep(2)
                success = start_service()
                sys.exit(0 if success else 1)
                
            elif command == 'console':
                run_console_mode()
                
            elif command == 'debug':
                # Enable debug logging
                logging.getLogger().setLevel(logging.DEBUG)
                logger.info("Debug mode enabled")
                run_console_mode()
                
            elif command in ['help', '--help', '-h']:
                show_usage()
                sys.exit(0)
                
            else:
                # Handle Windows Service commands
                import win32serviceutil
                win32serviceutil.HandleCommandLine(VoiceGuardService)
        else:
            # No arguments - run in console mode
            run_console_mode()
            
    except Exception as e:
        logger.error(f"Service startup error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
