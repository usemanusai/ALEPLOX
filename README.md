# VoiceGuard Emergency Shutdown Service

🎤 **AI-Powered Voice Command Emergency System Shutdown for Windows 11**

VoiceGuard is a robust Windows 11 background service that provides immediate system shutdown capability through AI-powered voice command recognition. Designed for emergency situations, accessibility needs, and critical system protection scenarios.

## 🚀 Key Features

### Core Functionality
- **24/7 Background Operation**: Windows Service with automatic startup and recovery
- **AI-Powered Recognition**: OpenRouter.ai integration with smart 30-key rotation system
- **Multi-Source Processing**: OpenRouter.ai + Windows Speech API + keyword matching fallback
- **Immediate Shutdown**: Emergency system shutdown equivalent to power loss
- **Dual-Process Architecture**: Secure Session 0 service + user-session audio helper

### Voice Command System
- **Configurable Commands**: Support for custom "magic words" and phrases
- **Adjustable Sensitivity**: Microphone sensitivity levels (low/medium/high)
- **Confidence Thresholds**: Customizable recognition accuracy settings
- **Multi-Word Support**: Both single words and complex phrases as triggers

### Safety & Reliability
- **Test Mode**: Safe command testing without actual shutdown execution
- **Confirmation Delays**: 2-3 second countdown with audio confirmation
- **Emergency Disable**: Multiple abort mechanisms (Ctrl+Alt+Shift+ESC)
- **Watchdog System**: Multi-layer monitoring with automatic restart
- **False Positive Protection**: Requires consecutive detections within 5 seconds

### User Interface
- **Configuration GUI**: Complete PyQt6 interface for all settings
- **System Tray Integration**: Real-time status monitoring and quick controls
- **Usage Analytics**: API key rotation optimization and cost tracking
- **Comprehensive Logging**: Structured logging with filtering and export

## 📋 System Requirements

### Operating System
- **Windows 11** (22H2 or later)
- **Architecture**: x64 only
- **Privileges**: Administrator rights for installation

### Software Dependencies
- **Python**: 3.11 or higher
- **.NET Runtime**: 8.0 or later
- **Visual C++ Redistributable**: 2022 or later

### Hardware Requirements
- **RAM**: Minimum 4GB, Recommended 8GB
- **Storage**: 500MB free space
- **Microphone**: Any Windows-compatible microphone
- **Network**: Internet connection for AI processing (optional for offline mode)

### API Requirements
- **OpenRouter.ai Account**: For enhanced AI recognition (optional)
- **API Keys**: Up to 30 keys for optimal performance (1,500 daily requests)

## 🔧 Installation

### Automated Installation (Recommended)

1. **Download the latest release** from the [Releases](https://github.com/yourusername/voiceguard/releases) page
2. **Run as Administrator**: Right-click `VoiceGuard-Setup.exe` → "Run as administrator"
3. **Follow the installer**: Complete the guided setup process
4. **Configure microphone permissions**: Allow microphone access in Windows Settings
5. **Launch configuration**: Run "VoiceGuard Configuration" from Start Menu

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/voiceguard.git
cd voiceguard

# Install Python dependencies
pip install -r requirements.txt

# Run installation script as Administrator
python install.py
```

### Post-Installation Setup

1. **Microphone Permissions**:
   - Open Windows Settings → Privacy & Security → Microphone
   - Enable "Microphone access" and "Let desktop apps access your microphone"

2. **Service Verification**:
   - Open Services (services.msc)
   - Verify "VoiceGuard Emergency Shutdown Service" is running

3. **Initial Configuration**:
   - Launch VoiceGuard Configuration
   - Complete the setup wizard
   - Test voice commands in Test Mode

## ⚙️ Configuration Guide

### Voice Commands Setup

1. **Open Configuration GUI**:
   ```
   Start Menu → VoiceGuard → VoiceGuard Configuration
   ```

2. **Add Voice Commands**:
   - Navigate to "Voice Commands" tab
   - Click "➕ Add Command"
   - Enter your emergency phrase (e.g., "emergency shutdown")
   - Set confidence threshold (recommended: 60-80%)
   - Enable the command

3. **Default Commands**:
   - "emergency shutdown"
   - "kill switch"
   - "force stop"
   - "shutdown now"

### Audio Settings Configuration

1. **Microphone Setup**:
   - Select your microphone device
   - Adjust sensitivity slider (recommended: 70-90%)
   - Test audio levels with real-time meter

2. **Recognition Settings**:
   - Set confidence threshold (60% recommended)
   - Enable noise suppression
   - Configure voice activity detection

### OpenRouter.ai API Integration

1. **Create OpenRouter.ai Account**:
   - Visit [OpenRouter.ai](https://openrouter.ai)
   - Sign up and verify your account
   - Generate API keys (up to 30 for optimal performance)

2. **Add API Keys**:
   - Open VoiceGuard Configuration
   - Navigate to "AI Configuration" tab
   - Click "📥 Import Keys"
   - Add your API keys (one per line)
   - Verify key functionality with "🧪 Test Keys"

3. **Key Rotation Strategy**:
   - **Smart Load Balancing** (recommended): Distributes load evenly
   - **Round Robin**: Sequential key usage
   - **Least Used First**: Prioritizes unused keys
   - **Random Selection**: Random key selection

### Safety Settings

1. **Confirmation Delay**:
   - Set delay between command detection and shutdown (3 seconds recommended)
   - Allows time for cancellation if needed

2. **Emergency Disable**:
   - Enable Ctrl+Alt+Shift+ESC emergency abort
   - Configure quiet hours to prevent accidental activation

3. **Test Mode**:
   - Always test new commands in Test Mode first
   - Commands are logged but no shutdown occurs
   - Auto-expires after 30 minutes for safety

## 🎯 Usage Instructions

### Normal Operation

1. **Service Status**: Check system tray icon for service status
   - 🟢 Green: Active and monitoring
   - 🟡 Yellow: Warning or limited functionality
   - 🔴 Red: Service not running
   - 🔵 Blue: Test mode active

2. **Voice Commands**: Speak your configured emergency phrase clearly
   - System will detect and process the command
   - 3-second confirmation countdown begins
   - System shuts down immediately after countdown

3. **Cancellation**: To abort a pending shutdown:
   - Press Ctrl+Alt+Shift+ESC immediately
   - Or use the system tray "Cancel Shutdown" option

### Test Mode Usage

1. **Enable Test Mode**:
   - Right-click system tray icon → "Toggle Test Mode"
   - Or use Configuration GUI → "🧪 Test Mode" button

2. **Testing Commands**:
   - Speak your voice commands normally
   - Commands are detected and logged
   - No actual shutdown occurs
   - Check logs for recognition accuracy

3. **Disable Test Mode**:
   - Test mode auto-expires after 30 minutes
   - Or manually disable via system tray/GUI

### Emergency Situations

⚠️ **CRITICAL SAFETY WARNINGS**:

- **Test thoroughly** before relying on VoiceGuard in emergencies
- **Have backup shutdown methods** available (physical power button, etc.)
- **Inform others** in your environment about the voice command system
- **Regular testing** ensures continued functionality
- **Keep API keys active** for optimal recognition accuracy

## 🔍 Troubleshooting

### Common Issues

#### Service Not Starting
```bash
# Check service status
sc query VoiceGuardService

# Restart service
sc stop VoiceGuardService
sc start VoiceGuardService

# Check logs
type "C:\ProgramData\VoiceGuard\logs\service.log"
```

#### Voice Commands Not Recognized
1. **Check microphone permissions** in Windows Settings
2. **Verify microphone device** in Configuration GUI
3. **Adjust sensitivity settings** (try 80-90%)
4. **Test in quiet environment** to eliminate background noise
5. **Check API key status** in AI Configuration tab

#### High CPU Usage
1. **Reduce audio buffer size** in Advanced settings
2. **Lower microphone sensitivity** to reduce processing
3. **Disable unnecessary features** (noise suppression, etc.)
4. **Check for conflicting audio software**

#### API Key Issues
1. **Verify key validity** with Test Keys function
2. **Check daily usage limits** (50 requests per key)
3. **Ensure keys are active** in OpenRouter.ai dashboard
4. **Add more keys** if hitting rate limits

### Log Analysis

**Log Locations**:
- Service logs: `C:\ProgramData\VoiceGuard\logs\service.log`
- Helper logs: `C:\ProgramData\VoiceGuard\logs\helper.log`
- GUI logs: `C:\ProgramData\VoiceGuard\logs\config_gui.log`

**Important Log Events**:
- Event ID 1001: Service started
- Event ID 2002: System shutdown initiated
- Event ID 3001: High CPU usage detected

### Getting Help

1. **Check Documentation**: Review this README and inline help
2. **View Logs**: Use Configuration GUI → Logs tab for detailed information
3. **GitHub Issues**: Report bugs at [Issues](https://github.com/yourusername/voiceguard/issues)
4. **Community Support**: Join discussions in [Discussions](https://github.com/yourusername/voiceguard/discussions)

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceGuard System                        │
├─────────────────────────────────────────────────────────────┤
│  Session 0 (Service Layer)          User Session (Audio)    │
│  ┌─────────────────────────┐       ┌─────────────────────┐  │
│  │   VoiceGuard Service    │◄─────►│  Audio Helper       │  │
│  │   - System Shutdown     │  IPC  │  - Microphone       │  │
│  │   - Watchdog Logic      │       │  - Speech Processing│  │
│  │   - Configuration       │       │  - AI Integration   │  │
│  │   - Event Logging       │       │  - System Tray      │  │
│  └─────────────────────────┘       └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

- **VoiceGuard Service**: Core Windows Service handling shutdown logic
- **Audio Helper**: User-session process for microphone access and AI processing
- **Configuration GUI**: PyQt6 application for system configuration
- **Watchdog System**: Multi-layer monitoring and recovery system
- **IPC Communication**: Secure Named Pipes for inter-process communication

### Security Model

- **Least Privilege**: Service runs with minimal required permissions
- **Session Isolation**: Audio processing isolated from critical shutdown logic
- **Encrypted Storage**: API keys and sensitive data encrypted with DPAPI
- **Access Control**: Named pipes protected with Windows ACLs

## 🤝 Contributing

We welcome contributions to VoiceGuard! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/voiceguard.git
cd voiceguard

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

### Code Style

- **Python**: Follow PEP 8 with Black formatting
- **Documentation**: Comprehensive docstrings for all functions
- **Testing**: Unit tests required for new features
- **Security**: Security review required for all changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

VoiceGuard is designed for emergency and accessibility use cases. Users are responsible for:

- **Testing thoroughly** before relying on the system
- **Understanding the risks** of automated system shutdown
- **Complying with local regulations** regarding emergency systems
- **Maintaining backup shutdown methods**

The developers are not liable for any damages resulting from the use or misuse of this software.

## 🙏 Acknowledgments

- **OpenRouter.ai** for providing AI speech recognition services
- **Microsoft** for Windows Speech Recognition APIs
- **PyQt6** for the configuration GUI framework
- **Contributors** who help improve VoiceGuard

---

**Made with ❤️ for emergency preparedness and accessibility**