# VoiceGuard Dependency Management System

## Overview

The VoiceGuard Dependency Management System is a comprehensive solution designed to prevent deprecated package warnings and ensure compatibility in the safety-critical emergency shutdown system. It provides automated dependency checking, version management, and error recovery mechanisms.

## Key Features

### 🔍 Pre-Installation Dependency Checker
- Automatically checks PyPI for latest compatible versions
- Validates all dependencies in requirements.txt and requirements-dev.txt
- Performs compatibility matrix validation before installation
- Creates backups before making changes

### 🧩 Version Compatibility Matrix
- Verifies Python version compatibility (3.8+ support)
- Checks for known incompatible package combinations
- Validates Windows-specific dependencies (pywin32, pystray, etc.)
- Ensures PyQt6 compatibility with target Windows version

### 🔄 Automated Update Mechanism
- Runs before each installation or service startup
- Updates requirements.txt with latest stable versions
- Maintains backups of working configurations
- Provides rollback capability if updates cause issues

### ⚠️ Deprecation Warning Handler
- Captures deprecation warnings during runtime
- Logs warnings for developer review without stopping execution
- Provides user-friendly notifications about upcoming changes
- Prevents warnings from terminating the emergency shutdown service

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Dependency Management System                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ DependencyManager│    │DependencyValidator│              │
│  │ - Version Check  │◄──►│ - Component Val. │              │
│  │ - Compatibility  │    │ - Integration   │              │
│  │ - Updates        │    │ - Reporting     │              │
│  │ - Backups        │    │ - History       │              │
│  └─────────────────┘    └─────────────────┘              │
│           │                       │                        │
│           ▼                       ▼                        │
│  ┌─────────────────────────────────────────────────────────┤
│  │              Integration Points                         │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │ │install.py   │ │main_service │ │main_helper/config   ││
│  │ │- Pre-check  │ │- Startup    │ │- Component specific ││
│  │ │- Auto-update│ │- Validation │ │- Audio/GUI checks   ││
│  │ └─────────────┘ └─────────────┘ └─────────────────────┘│
│  └─────────────────────────────────────────────────────────┤
│           │                       │                        │
│           ▼                       ▼                        │
│  ┌─────────────────┐    ┌─────────────────┐              │
│  │ Watchdog System │    │ CLI Management  │              │
│  │ - Health Monitor │    │ - Manual Ops   │              │
│  │ - Dep. Checking │    │ - Reporting     │              │
│  └─────────────────┘    └─────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### DependencyManager (`src/dependency_manager.py`)
Core dependency management functionality:
- **System Compatibility**: Checks Python/Windows versions
- **Version Fetching**: Gets latest versions from PyPI
- **Compatibility Matrix**: Validates package combinations
- **Backup/Restore**: Configuration backup and rollback
- **Warning Handling**: Captures and manages deprecation warnings

### DependencyValidator (`src/dependency_validator.py`)
Integration and validation for VoiceGuard components:
- **Service Validation**: Validates dependencies for service startup
- **GUI Validation**: Checks GUI-specific dependencies (PyQt6, Pillow)
- **Audio Validation**: Validates audio processing dependencies
- **Installation Validation**: Pre-installation dependency checks

### CLI Tool (`src/dependency_cli.py`)
Command-line interface for manual operations:
```bash
python src/dependency_cli.py check          # Check dependency status
python src/dependency_cli.py update         # Update dependencies
python src/dependency_cli.py validate gui   # Validate GUI dependencies
python src/dependency_cli.py backup         # Create backup
python src/dependency_cli.py restore <path> # Restore from backup
python src/dependency_cli.py cleanup        # Clean old data
```

## Integration Points

### 1. Installation (`install.py`)
```python
# Pre-installation dependency check
if DEPENDENCY_VALIDATION_AVAILABLE:
    success, results = dependency_validator.validate_for_installation(requirements_files)
    if not success:
        # Handle validation failures
        return False
```

### 2. Service Startup (`main_service.py`)
```python
# Validate dependencies before starting service
validation_ok, results = await dependency_validator.validate_for_service_startup()
if not validation_ok and not results.get('fallback_enabled'):
    sys.exit(1)
```

### 3. Audio Helper (`main_helper.py`)
```python
# Validate audio dependencies
audio_validation_ok, results = dependency_validator.validate_for_audio_processing()
if not audio_validation_ok:
    # Log issues but continue with basic checks
    logger.warning("Audio dependency validation failed")
```

### 4. Configuration GUI (`main_config.py`)
```python
# Validate GUI dependencies
gui_validation_ok, results = dependency_validator.validate_for_gui_startup()
if not gui_validation_ok:
    show_error_dialog("GUI Dependencies Missing", issues)
    sys.exit(1)
```

### 5. Watchdog System (`watchdog_system.py`)
```python
# Monitor dependency health
health_status['dependencies'] = self.dependency_watchdog.check_health()
```

## Configuration

### Dependency Configuration (`config/dependency_config.json`)
Comprehensive configuration for dependency management:
- **Compatibility Matrix**: Package version constraints
- **Known Good Versions**: Tested and verified package versions
- **Update Policies**: Rules for different types of updates
- **Validation Rules**: Component-specific validation requirements
- **Warning Filters**: Control which warnings to suppress/log
- **Fallback Configuration**: Emergency fallback settings

### Key Settings
```json
{
  "settings": {
    "auto_update_enabled": false,
    "update_check_interval_hours": 24,
    "emergency_fallback_enabled": true
  },
  "compatibility_matrix": {
    "python_versions": {
      "minimum": "3.8.0",
      "recommended": "3.11.0"
    }
  }
}
```

## Error Recovery

### Network Issues
- Automatic fallback to cached version information
- Graceful degradation when PyPI is unreachable
- Local validation using known good versions

### Package Conflicts
- Automatic detection of incompatible combinations
- Rollback to previous working configuration
- Emergency fallback mode for critical operations

### Import Failures
- Emergency warning suppression
- Fallback to basic functionality
- Detailed logging for troubleshooting

## Usage Examples

### Basic Dependency Check
```bash
# Check current dependency status
python src/dependency_cli.py check

# Output:
# 📊 System Information:
#   Python Version: 3.11.9
#   Platform: Windows-10-10.0.22631-SP0
# ✅ Dependency Validation: PASSED
# ⚠️ Warnings Summary: 5 recent warnings
```

### Update Dependencies
```bash
# Check for and apply updates
python src/dependency_cli.py update

# Output:
# 📦 Found 3 package updates:
#   numpy: 1.24.0 → 1.26.4
#   scipy: 1.10.0 → 1.13.1
# 📁 Backup created: /path/to/backup
# ✅ Requirements files updated successfully
```

### Component Validation
```bash
# Validate specific components
python src/dependency_cli.py validate audio

# Output:
# ✅ Audio dependencies validated successfully
# 🎤 Audio devices found: 2
```

## Monitoring and Alerts

### Health Monitoring
- Continuous dependency health checking
- Integration with watchdog system
- Automatic recovery actions

### Warning Collection
- Real-time deprecation warning capture
- Categorization and analysis
- Developer notification system

### Performance Tracking
- Validation performance metrics
- Update success/failure rates
- System compatibility trends

## Best Practices

### For Developers
1. **Always run dependency checks** before major changes
2. **Create backups** before updating dependencies
3. **Test in isolated environments** before production deployment
4. **Monitor warning logs** regularly for upcoming issues

### For Production
1. **Enable emergency fallback mode** for critical systems
2. **Schedule regular dependency health checks**
3. **Maintain multiple backup configurations**
4. **Monitor system compatibility continuously**

### For Updates
1. **Use manual approval** for critical package updates
2. **Test updates thoroughly** in development environment
3. **Have rollback plan ready** before applying updates
4. **Document all dependency changes**

## Troubleshooting

### Common Issues

#### "Dependency validation failed"
- Check system compatibility (Python/Windows versions)
- Verify all required packages are installed
- Run `dependency_cli.py check` for detailed diagnosis

#### "Network error during update check"
- System will automatically fallback to cached versions
- Check internet connectivity
- Verify PyPI accessibility

#### "Package import failed"
- Emergency fallback mode will be activated
- Check package installation: `pip list`
- Restore from backup if necessary

#### "Incompatible package combination"
- Review compatibility matrix in configuration
- Update conflicting packages to compatible versions
- Use `dependency_cli.py update` to resolve automatically

### Debug Mode
Enable verbose logging for troubleshooting:
```bash
python src/dependency_cli.py -v check
```

## Security Considerations

### Package Verification
- Validates packages against known good versions
- Checks for security updates automatically
- Maintains audit trail of all changes

### Backup Security
- Encrypted storage of sensitive configuration
- Secure backup locations with proper permissions
- Automatic cleanup of old backups

### Network Security
- HTTPS-only communication with PyPI
- Timeout protection for network operations
- Fallback mechanisms for network failures

## Future Enhancements

### Planned Features
- **Automated Security Scanning**: Integration with vulnerability databases
- **Machine Learning**: Predictive compatibility analysis
- **Cloud Integration**: Centralized dependency management
- **Advanced Analytics**: Dependency usage patterns and optimization

### Extensibility
The system is designed to be extensible:
- Plugin architecture for custom validators
- Configurable compatibility rules
- Custom warning handlers
- Integration with external monitoring systems

---

For more information, see the source code documentation and configuration examples in the `config/` directory.
