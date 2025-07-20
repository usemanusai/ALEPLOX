#!/usr/bin/env python3
"""
VoiceGuard Audio Helper Process
User session process for audio monitoring and AI integration
"""

import sys
import os
import asyncio
import logging
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import VoiceGuard components
from audio_helper import AudioHelperProcess
from system_tray import SystemTrayApp


def setup_helper_environment():
    """Setup helper process environment"""
    # Ensure data directories exist
    data_dir = Path("C:/ProgramData/VoiceGuard")
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = logs_dir / "helper.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("VoiceGuardHelper")
    logger.info("VoiceGuard helper process environment initialized")
    
    return logger


def check_audio_prerequisites():
    """Check audio-related prerequisites"""
    logger = logging.getLogger("AudioPrerequisites")
    
    # Check PyAudio availability
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
            logger.warning("No audio input devices found")
            return False
            
        logger.info(f"Found {len(input_devices)} audio input devices")
        return True
        
    except Exception as e:
        logger.error(f"Audio system check failed: {e}")
        return False


def check_service_connection():
    """Check if VoiceGuard service is running"""
    logger = logging.getLogger("ServiceConnection")
    
    try:
        import win32serviceutil
        
        # Check service status
        status = win32serviceutil.QueryServiceStatus("VoiceGuardService")
        service_state = status[1]
        
        if service_state == 4:  # SERVICE_RUNNING
            logger.info("VoiceGuard service is running")
            return True
        else:
            logger.warning(f"VoiceGuard service not running (state: {service_state})")
            return False
            
    except Exception as e:
        logger.error(f"Service connection check failed: {e}")
        return False


async def run_helper_with_tray():
    """Run helper process with system tray"""
    logger = logging.getLogger("HelperWithTray")
    
    try:
        # Create helper and tray
        helper = AudioHelperProcess()
        
        # Setup graceful shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info("Received shutdown signal")
            shutdown_event.set()
            
        # Setup signal handlers (Windows doesn't support all POSIX signals)
        try:
            import signal
            signal.signal(signal.SIGINT, lambda s, f: signal_handler())
            signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        except AttributeError:
            # Some signals not available on Windows
            pass
            
        # Start helper process
        logger.info("Starting audio helper process...")
        helper_task = asyncio.create_task(helper.start())
        
        # Wait for shutdown signal or helper completion
        done, pending = await asyncio.wait(
            [helper_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cleanup
        logger.info("Shutting down helper process...")
        helper.is_running = False
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
        # Wait for helper to finish
        try:
            await asyncio.wait_for(helper_task, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Helper process shutdown timeout")
            
    except Exception as e:
        logger.error(f"Helper process error: {e}")
        raise


async def run_helper_headless():
    """Run helper process without system tray (headless mode)"""
    logger = logging.getLogger("HelperHeadless")
    
    try:
        # Create helper
        helper = AudioHelperProcess()
        
        # Disable system tray
        helper.system_tray = None
        
        logger.info("Starting audio helper in headless mode...")
        await helper.start()
        
    except Exception as e:
        logger.error(f"Headless helper error: {e}")
        raise


def run_audio_test():
    """Run audio system test"""
    logger = logging.getLogger("AudioTest")
    
    try:
        import pyaudio
        import numpy as np
        import time
        
        logger.info("Starting audio test...")
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # List audio devices
        logger.info("Available audio input devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                logger.info(f"  {i}: {device_info['name']} ({device_info['maxInputChannels']} channels)")
                
        # Test default microphone
        try:
            logger.info("Testing default microphone for 5 seconds...")
            
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            max_level = 0
            for _ in range(int(16000 / 1024 * 5)):  # 5 seconds
                data = stream.read(1024)
                audio_data = np.frombuffer(data, dtype=np.int16)
                level = np.max(np.abs(audio_data))
                max_level = max(max_level, level)
                
            stream.stop_stream()
            stream.close()
            
            logger.info(f"Audio test completed. Max level: {max_level} ({max_level/32767*100:.1f}%)")
            
            if max_level > 1000:
                logger.info("✅ Microphone is working and detecting audio")
            else:
                logger.warning("⚠️ Microphone may not be working or very quiet")
                
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            
        audio.terminate()
        
    except Exception as e:
        logger.error(f"Audio test failed: {e}")


def show_usage():
    """Show usage information"""
    print("""
VoiceGuard Audio Helper Process

Usage:
    python main_helper.py [command]

Commands:
    run         Run helper with system tray (default)
    headless    Run helper without system tray
    test        Test audio system
    debug       Run in debug mode with verbose logging
    
Examples:
    python main_helper.py
    python main_helper.py headless
    python main_helper.py test
    """)


async def main_async():
    """Main async entry point for helper process"""
    logger = setup_helper_environment()
    
    try:
        # Parse command line arguments
        command = sys.argv[1].lower() if len(sys.argv) > 1 else 'run'
        
        if command in ['help', '--help', '-h']:
            show_usage()
            return
            
        elif command == 'test':
            run_audio_test()
            return
            
        elif command == 'debug':
            # Enable debug logging
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug mode enabled")
            command = 'run'  # Continue with normal run
            
        # Check prerequisites
        if not check_audio_prerequisites():
            logger.error("Audio prerequisites not met")
            sys.exit(1)
            
        # Check service connection (warn but don't fail)
        if not check_service_connection():
            logger.warning("VoiceGuard service not running - some features may not work")
            
        # Run based on command
        if command == 'headless':
            await run_helper_headless()
        else:  # 'run' or default
            await run_helper_with_tray()
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Helper process error: {e}")
        sys.exit(1)


def main():
    """Main entry point for helper process"""
    if sys.platform == "win32":
        # Set event loop policy for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    # Run async main
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
