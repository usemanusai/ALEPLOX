#!/usr/bin/env python3
"""
VoiceGuard Dependency Management CLI
Command-line interface for dependency management operations
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

from dependency_manager import DependencyManager
from dependency_validator import dependency_validator


def setup_logging(verbose: bool = False):
    """Setup logging for CLI"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def cmd_check(args):
    """Check dependency status"""
    print("🔍 Checking dependency status...")
    
    try:
        # Get comprehensive status
        status = dependency_validator.get_validation_report()
        
        # Display system info
        system_info = status.get('dependency_status', {}).get('system_info', {})
        print(f"\n📊 System Information:")
        print(f"  Python Version: {system_info.get('python_version', 'Unknown')}")
        print(f"  Platform: {system_info.get('platform', 'Unknown')}")
        print(f"  Architecture: {system_info.get('architecture', 'Unknown')}")
        
        # Display validation status
        validation_status = status.get('dependency_status', {}).get('validation_status', {})
        if validation_status.get('passed', True):
            print(f"\n✅ Dependency Validation: PASSED")
        else:
            print(f"\n❌ Dependency Validation: FAILED")
            for issue in validation_status.get('issues', []):
                print(f"  - {issue}")
                
        # Display warnings summary
        warnings_summary = status.get('dependency_status', {}).get('warnings_summary', {})
        total_warnings = warnings_summary.get('total_warnings', 0)
        recent_warnings = warnings_summary.get('recent_warnings', 0)
        
        print(f"\n⚠️ Warnings Summary:")
        print(f"  Total Warnings: {total_warnings}")
        print(f"  Recent Warnings (24h): {recent_warnings}")
        
        if warnings_summary.get('categories'):
            print(f"  Categories:")
            for category, count in warnings_summary['categories'].items():
                print(f"    {category}: {count}")
                
        # Display recommendations
        recommendations = status.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
        else:
            print(f"\n✅ No recommendations - system is healthy")
            
    except Exception as e:
        print(f"❌ Error checking dependency status: {e}")
        return 1
        
    return 0


def cmd_update(args):
    """Update dependencies"""
    print("🔄 Updating dependencies...")
    
    try:
        manager = DependencyManager()
        
        # Parse requirements files
        requirements_files = [
            Path("requirements.txt"),
            Path("requirements-dev.txt")
        ]
        
        existing_files = [f for f in requirements_files if f.exists()]
        
        if not existing_files:
            print("❌ No requirements files found")
            return 1
            
        # Run pre-installation check
        success, results = manager.pre_installation_check(existing_files)
        
        if not success:
            print("❌ Pre-installation check failed:")
            for issue in results.get('system_issues', []):
                print(f"  - System: {issue}")
            for issue in results.get('incompatibilities', []):
                print(f"  - Compatibility: {issue}")
            return 1
            
        # Check for updates
        updates = results.get('package_updates', {})
        
        if not updates:
            print("✅ All packages are up to date")
            return 0
            
        print(f"📦 Found {len(updates)} package updates:")
        for package, info in updates.items():
            current = info.get('current', 'not_installed')
            latest = info.get('latest', 'unknown')
            print(f"  {package}: {current} → {latest}")
            
        # Confirm update
        if not args.yes:
            response = input("\nProceed with updates? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                print("Update cancelled")
                return 0
                
        # Create backup
        backup_path = manager.backup_current_configuration()
        print(f"📁 Backup created: {backup_path}")
        
        # Apply updates
        update_dict = {
            pkg: info['latest'] 
            for pkg, info in updates.items()
            if info['latest']
        }
        
        success = manager.update_requirements_files(update_dict, backup_path)
        
        if success:
            print("✅ Requirements files updated successfully")
            print(f"💾 Backup available at: {backup_path}")
            print("\n⚠️ Run 'pip install -r requirements.txt' to install updated packages")
        else:
            print("❌ Failed to update requirements files")
            return 1
            
    except Exception as e:
        print(f"❌ Error updating dependencies: {e}")
        return 1
        
    return 0


def cmd_validate(args):
    """Validate specific component dependencies"""
    print(f"🔍 Validating {args.component} dependencies...")
    
    try:
        if args.component == 'service':
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            success, results = loop.run_until_complete(
                dependency_validator.validate_for_service_startup()
            )
            loop.close()
            
        elif args.component == 'gui':
            success, results = dependency_validator.validate_for_gui_startup()
            
        elif args.component == 'audio':
            success, results = dependency_validator.validate_for_audio_processing()
            
        else:
            print(f"❌ Unknown component: {args.component}")
            return 1
            
        if success:
            print(f"✅ {args.component.title()} dependencies validated successfully")
            
            # Show additional info
            if 'audio_devices_found' in results:
                print(f"🎤 Audio devices found: {results['audio_devices_found']}")
                
        else:
            print(f"❌ {args.component.title()} dependency validation failed:")
            for issue in results.get('issues', []):
                print(f"  - {issue}")
                
        # Record validation
        dependency_validator.record_validation_result(
            f'cli_{args.component}_validation',
            success,
            results
        )
        
    except Exception as e:
        print(f"❌ Error validating {args.component} dependencies: {e}")
        return 1
        
    return 0 if success else 1


def cmd_backup(args):
    """Create dependency configuration backup"""
    print("💾 Creating dependency backup...")
    
    try:
        manager = DependencyManager()
        backup_path = manager.backup_current_configuration()
        
        print(f"✅ Backup created successfully:")
        print(f"📁 Location: {backup_path}")
        
        # List backup contents
        backup_files = list(backup_path.glob("*"))
        print(f"📄 Files backed up:")
        for file in backup_files:
            print(f"  - {file.name}")
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return 1
        
    return 0


def cmd_restore(args):
    """Restore from dependency backup"""
    backup_path = Path(args.backup_path)
    
    if not backup_path.exists():
        print(f"❌ Backup path does not exist: {backup_path}")
        return 1
        
    print(f"🔄 Restoring from backup: {backup_path}")
    
    try:
        manager = DependencyManager()
        
        # Confirm restore
        if not args.yes:
            response = input("This will overwrite current configuration. Continue? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                print("Restore cancelled")
                return 0
                
        success = manager.rollback_to_backup(backup_path)
        
        if success:
            print("✅ Configuration restored successfully")
            print("⚠️ Run 'pip install -r requirements.txt' to install restored packages")
        else:
            print("❌ Failed to restore configuration")
            return 1
            
    except Exception as e:
        print(f"❌ Error restoring backup: {e}")
        return 1
        
    return 0


def cmd_cleanup(args):
    """Clean up old dependency data"""
    print("🧹 Cleaning up old dependency data...")
    
    try:
        manager = DependencyManager()
        manager.cleanup_old_data(args.days)
        
        print(f"✅ Cleaned up data older than {args.days} days")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 1
        
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="VoiceGuard Dependency Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check dependency status')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update dependencies')
    update_parser.add_argument('-y', '--yes', action='store_true',
                              help='Automatically confirm updates')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate component dependencies')
    validate_parser.add_argument('component', choices=['service', 'gui', 'audio'],
                                help='Component to validate')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create dependency backup')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_path', help='Path to backup directory')
    restore_parser.add_argument('-y', '--yes', action='store_true',
                               help='Automatically confirm restore')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--days', type=int, default=30,
                               help='Keep data newer than N days (default: 30)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    setup_logging(args.verbose)
    
    # Execute command
    commands = {
        'check': cmd_check,
        'update': cmd_update,
        'validate': cmd_validate,
        'backup': cmd_backup,
        'restore': cmd_restore,
        'cleanup': cmd_cleanup
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
