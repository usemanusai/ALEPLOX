#!/usr/bin/env python3
"""
VoiceGuard Dependency Management System Demo
Demonstrates the automated dependency management capabilities
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dependency_manager import DependencyManager
    from dependency_validator import dependency_validator
    DEPENDENCY_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"❌ Dependency system not available: {e}")
    DEPENDENCY_SYSTEM_AVAILABLE = False


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🎤 {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print formatted section"""
    print(f"\n📋 {title}")
    print("-" * 40)


async def demo_dependency_management():
    """Demonstrate dependency management system"""
    
    if not DEPENDENCY_SYSTEM_AVAILABLE:
        print("❌ Dependency management system not available")
        return
        
    print_header("VoiceGuard Dependency Management System Demo")
    
    # Initialize dependency manager
    manager = DependencyManager()
    
    # 1. System Compatibility Check
    print_section("System Compatibility Check")
    
    try:
        compatible, issues = manager.check_system_compatibility()
        
        if compatible:
            print("✅ System compatibility: PASSED")
        else:
            print("❌ System compatibility: FAILED")
            for issue in issues:
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"❌ System compatibility check error: {e}")
    
    # 2. Dependency Status Report
    print_section("Dependency Status Report")
    
    try:
        status = dependency_validator.get_validation_report()
        
        # System info
        system_info = status.get('dependency_status', {}).get('system_info', {})
        print(f"🖥️ System Information:")
        print(f"  Python Version: {system_info.get('python_version', 'Unknown')}")
        print(f"  Platform: {system_info.get('platform', 'Unknown')}")
        print(f"  Architecture: {system_info.get('architecture', 'Unknown')}")
        
        # Validation status
        validation_status = status.get('dependency_status', {}).get('validation_status', {})
        if validation_status.get('passed', True):
            print(f"✅ Dependency Validation: PASSED")
        else:
            print(f"❌ Dependency Validation: FAILED")
            for issue in validation_status.get('issues', []):
                print(f"  - {issue}")
                
        # Warnings summary
        warnings_summary = status.get('dependency_status', {}).get('warnings_summary', {})
        total_warnings = warnings_summary.get('total_warnings', 0)
        recent_warnings = warnings_summary.get('recent_warnings', 0)
        
        print(f"⚠️ Warnings: {total_warnings} total, {recent_warnings} recent")
        
        # Recommendations
        recommendations = status.get('recommendations', [])
        if recommendations:
            print(f"💡 Recommendations:")
            for rec in recommendations[:3]:  # Show first 3
                print(f"  - {rec}")
        else:
            print(f"✅ No recommendations - system is healthy")
            
    except Exception as e:
        print(f"❌ Status report error: {e}")
    
    # 3. Component Validation Demo
    print_section("Component Validation Demo")
    
    # Service validation
    try:
        print("🔍 Validating service dependencies...")
        success, results = await dependency_validator.validate_for_service_startup()
        
        if success:
            print("✅ Service dependencies: VALIDATED")
            if results.get('status') == 'fallback_mode':
                print("⚠️ Running in emergency fallback mode")
        else:
            print("❌ Service dependencies: FAILED")
            for issue in results.get('issues', []):
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"❌ Service validation error: {e}")
    
    # GUI validation
    try:
        print("🔍 Validating GUI dependencies...")
        success, results = dependency_validator.validate_for_gui_startup()
        
        if success:
            print("✅ GUI dependencies: VALIDATED")
        else:
            print("❌ GUI dependencies: FAILED")
            for issue in results.get('issues', []):
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"❌ GUI validation error: {e}")
    
    # Audio validation
    try:
        print("🔍 Validating audio dependencies...")
        success, results = dependency_validator.validate_for_audio_processing()
        
        if success:
            print("✅ Audio dependencies: VALIDATED")
            devices_found = results.get('audio_devices_found', 0)
            if devices_found > 0:
                print(f"🎤 Audio devices found: {devices_found}")
        else:
            print("❌ Audio dependencies: FAILED")
            for issue in results.get('issues', []):
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"❌ Audio validation error: {e}")
    
    # 4. Update Check Demo
    print_section("Update Check Demo")
    
    try:
        print("🔍 Checking for dependency updates...")
        success, results = manager.automated_update_check()
        
        if results.get('skipped'):
            print("⏭️ Update check skipped (recent check)")
        elif results.get('fallback_mode'):
            print("⚠️ Using cached dependency information (network issues)")
        else:
            updates = results.get('package_updates', {})
            if updates:
                print(f"📦 Found {len(updates)} package updates available:")
                for package, info in list(updates.items())[:5]:  # Show first 5
                    current = info.get('current', 'not_installed')
                    latest = info.get('latest', 'unknown')
                    print(f"  {package}: {current} → {latest}")
            else:
                print("✅ All packages are up to date")
                
    except Exception as e:
        print(f"❌ Update check error: {e}")
    
    # 5. Warning Handler Demo
    print_section("Warning Handler Demo")
    
    try:
        import warnings
        
        print("🔍 Testing warning handler...")
        
        # Generate test warnings
        warnings.warn("Test deprecation warning", DeprecationWarning)
        warnings.warn("Test future warning", FutureWarning)
        
        print("✅ Warning handler active - warnings captured without terminating execution")
        
        # Show warning statistics
        warnings_summary = manager._get_warnings_summary()
        if warnings_summary.get('total_warnings', 0) > 0:
            print(f"📊 Warning statistics:")
            print(f"  Total warnings: {warnings_summary['total_warnings']}")
            print(f"  Recent warnings: {warnings_summary['recent_warnings']}")
            
            categories = warnings_summary.get('categories', {})
            if categories:
                print(f"  Categories: {', '.join(categories.keys())}")
                
    except Exception as e:
        print(f"❌ Warning handler demo error: {e}")
    
    # 6. Emergency Fallback Demo
    print_section("Emergency Fallback Demo")
    
    try:
        print("🔍 Testing emergency fallback mode...")
        
        success = manager.emergency_fallback_mode()
        
        if success:
            print("✅ Emergency fallback mode: ACTIVATED")
            print("  - All non-critical warnings suppressed")
            print("  - Using known good package versions")
            print("  - System ready for critical operation")
        else:
            print("❌ Emergency fallback mode: FAILED")
            
    except Exception as e:
        print(f"❌ Emergency fallback demo error: {e}")
    
    # 7. Summary
    print_section("Demo Summary")
    
    print("🎯 VoiceGuard Dependency Management System Features Demonstrated:")
    print("  ✅ System compatibility validation")
    print("  ✅ Component-specific dependency checking")
    print("  ✅ Automated update detection")
    print("  ✅ Warning capture and suppression")
    print("  ✅ Emergency fallback mode")
    print("  ✅ Comprehensive status reporting")
    
    print("\n💡 Key Benefits:")
    print("  - Prevents deprecated package warnings from stopping the service")
    print("  - Ensures compatibility across all VoiceGuard components")
    print("  - Provides graceful degradation during dependency issues")
    print("  - Maintains system reliability for emergency shutdown operations")
    
    print("\n🔧 Available CLI Commands:")
    print("  python src/dependency_cli.py check          # Check status")
    print("  python src/dependency_cli.py update         # Update dependencies")
    print("  python src/dependency_cli.py validate gui   # Validate components")
    print("  python src/dependency_cli.py backup         # Create backup")
    print("  python src/dependency_cli.py cleanup        # Clean old data")


def main():
    """Main demo entry point"""
    try:
        # Run async demo
        asyncio.run(demo_dependency_management())
        
        print(f"\n{'='*60}")
        print("🎤 VoiceGuard Dependency Management Demo Complete!")
        print("📚 See docs/DEPENDENCY_MANAGEMENT.md for detailed documentation")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())
