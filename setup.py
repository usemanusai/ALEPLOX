#!/usr/bin/env python3
"""
VoiceGuard Emergency Shutdown Service
Setup script for packaging and distribution
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "AI-Powered Voice Command Emergency System Shutdown for Windows 11"

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() 
            for line in f.readlines() 
            if line.strip() and not line.startswith("#")
        ]
else:
    requirements = [
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "pyaudio>=0.2.11",
        "librosa>=0.10.0",
        "webrtcvad>=2.0.10",
        "SpeechRecognition>=3.10.0",
        "aiohttp>=3.8.0",
        "PyQt6>=6.5.0",
        "pywin32>=306",
        "psutil>=5.9.0",
        "Pillow>=10.0.0",
        "cryptography>=41.0.0",
        "pyyaml>=6.0"
    ]

setup(
    name="voiceguard",
    version="1.0.0",
    author="VoiceGuard Team",
    author_email="support@voiceguard.local",
    description="AI-Powered Voice Command Emergency System Shutdown for Windows 11",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/voiceguard",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/voiceguard/issues",
        "Source": "https://github.com/yourusername/voiceguard",
        "Documentation": "https://github.com/yourusername/voiceguard/blob/main/README.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Systems Administration",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Environment :: Win32 (MS Windows)",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "advanced": [
            "tensorflow>=2.13.0",
            "torch>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "voiceguard-service=main_service:main",
            "voiceguard-helper=main_helper:main",
            "voiceguard-config=main_config:main",
        ],
    },
    include_package_data=True,
    package_data={
        "voiceguard": [
            "*.json",
            "*.yaml",
            "*.yml",
            "templates/*.html",
            "static/*",
        ],
    },
    zip_safe=False,
    keywords=[
        "voice recognition",
        "emergency shutdown",
        "accessibility",
        "windows service",
        "ai speech",
        "system automation",
        "emergency response"
    ],
    platforms=["Windows"],
    license="MIT",
    
    # Windows-specific metadata
    options={
        "bdist_wininst": {
            "title": "VoiceGuard Emergency Shutdown Service",
            "bitmap": "installer/voiceguard_banner.bmp",
            "install_script": "install.py",
        },
        "bdist_msi": {
            "upgrade_code": "{12345678-1234-5678-9012-123456789012}",
            "add_to_path": False,
            "initial_target_dir": r"[ProgramFilesFolder]\VoiceGuard",
        },
    },
)
