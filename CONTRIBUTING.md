# Contributing to VoiceGuard

Thank you for your interest in contributing to VoiceGuard! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use the issue templates** when available
3. **Provide detailed information**:
   - Windows version and build
   - Python version
   - VoiceGuard version
   - Steps to reproduce
   - Expected vs actual behavior
   - Log files (if applicable)

### Suggesting Features

1. **Check the roadmap** and existing feature requests
2. **Open a discussion** before creating a feature request
3. **Describe the use case** and why it's needed
4. **Consider security implications** for emergency systems

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** from `main`
3. **Follow coding standards** (see below)
4. **Write tests** for new functionality
5. **Update documentation** as needed
6. **Submit a pull request**

## 🛠️ Development Setup

### Prerequisites

- **Windows 11** (22H2 or later)
- **Python 3.11+**
- **Git**
- **Visual Studio Code** (recommended)

### Environment Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/voiceguard.git
cd voiceguard

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_config_manager.py

# Run with verbose output
python -m pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## 📝 Coding Standards

### Python Style

- **Follow PEP 8** with Black formatting
- **Line length**: 88 characters (Black default)
- **Import order**: isort configuration
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all modules, classes, and functions

### Code Organization

```python
#!/usr/bin/env python3
"""
Module docstring describing purpose and usage.
"""

import standard_library
import third_party
from local_module import LocalClass

# Constants
CONSTANT_VALUE = "value"

class ExampleClass:
    """Class docstring."""
    
    def __init__(self, param: str):
        """Initialize with parameter."""
        self.param = param
        
    def public_method(self, arg: int) -> bool:
        """Public method with type hints and docstring."""
        return self._private_method(arg)
        
    def _private_method(self, arg: int) -> bool:
        """Private method (underscore prefix)."""
        return arg > 0
```

### Error Handling

```python
# Use specific exceptions
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle or re-raise as appropriate

# Log errors with context
logger.error(f"Failed to process {item_name}: {e}", exc_info=True)
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning about potential issues")
logger.error("Error that doesn't stop execution")
logger.critical("Critical error that may stop execution")
```

## 🧪 Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from src.module import ClassToTest

class TestClassToTest:
    """Test class following naming convention."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.instance = ClassToTest()
        
    def test_method_success_case(self):
        """Test successful operation."""
        result = self.instance.method("valid_input")
        assert result == expected_value
        
    def test_method_error_case(self):
        """Test error handling."""
        with pytest.raises(SpecificException):
            self.instance.method("invalid_input")
            
    @patch('src.module.external_dependency')
    def test_method_with_mock(self, mock_dependency):
        """Test with mocked dependencies."""
        mock_dependency.return_value = "mocked_result"
        result = self.instance.method_using_dependency()
        assert result == "expected_result"
```

### Test Categories

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **System Tests**: Test end-to-end functionality
- **Security Tests**: Test security-related functionality

### Test Requirements

- **Coverage**: Minimum 80% code coverage
- **Isolation**: Tests should not depend on each other
- **Deterministic**: Tests should produce consistent results
- **Fast**: Unit tests should run quickly

## 🔒 Security Considerations

### Security Review Required

All contributions involving these areas require security review:

- **Authentication/Authorization**
- **Cryptography/Encryption**
- **Network Communication**
- **File System Access**
- **Registry Modifications**
- **Service/Process Management**

### Security Best Practices

- **Principle of Least Privilege**: Request minimal permissions
- **Input Validation**: Validate all external inputs
- **Secure Defaults**: Default to secure configurations
- **Error Handling**: Don't leak sensitive information in errors
- **Logging**: Don't log sensitive data

## 📚 Documentation

### Code Documentation

- **Module docstrings**: Describe purpose and usage
- **Class docstrings**: Describe class purpose and key methods
- **Function docstrings**: Describe parameters, return values, and exceptions
- **Inline comments**: Explain complex logic

### User Documentation

- **README updates**: Keep installation and usage instructions current
- **Configuration guides**: Document new settings and options
- **Troubleshooting**: Add common issues and solutions
- **Examples**: Provide usage examples for new features

## 🚀 Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version** in `setup.py` and `__init__.py`
2. **Update CHANGELOG.md** with new features and fixes
3. **Run full test suite** and ensure all tests pass
4. **Update documentation** as needed
5. **Create release PR** and get approval
6. **Tag release** after merging
7. **Build and test installer** on clean Windows 11 system
8. **Publish release** with release notes

## 🎯 Roadmap and Priorities

### High Priority

- **Security enhancements**
- **Performance optimizations**
- **Bug fixes**
- **Documentation improvements**

### Medium Priority

- **New voice recognition engines**
- **Additional configuration options**
- **Improved error handling**
- **Better logging and diagnostics**

### Low Priority

- **UI/UX improvements**
- **Additional languages**
- **Advanced features**
- **Integration with other systems**

## 💬 Communication

### Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and discussion

### Guidelines

- **Be respectful** and professional
- **Stay on topic** and provide context
- **Search before posting** to avoid duplicates
- **Use clear titles** and descriptions

## 📄 License

By contributing to VoiceGuard, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

If you have questions about contributing, please:

1. **Check the documentation** first
2. **Search existing issues** and discussions
3. **Open a new discussion** if needed

Thank you for contributing to VoiceGuard! 🎤
