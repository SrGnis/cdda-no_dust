#!/usr/bin/env python3
"""
Setup script for CDDA No Dust

This script helps set up the no dust system and provides
convenient commands for common operations.
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.no_dust.config import Config
from src.no_dust.version_tracker import VersionTracker
from src.no_dust.git_manager import GitManager
from src.no_dust.utils import setup_logging


def setup_system():
    """Set up the no dust system for first use."""
    print("Setting up CDDA No Dust...")
    
    # Create default configuration if it doesn't exist
    config_file = Path("config.json")
    if not config_file.exists():
        print("Creating default configuration...")
        config = Config()
        config.save_to_file("config.json")
        print("✓ Created config.json")
    else:
        print("✓ Configuration file already exists")
    
    # Validate configuration
    config = Config.load_from_file("config.json")
    errors = config.validate()
    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✓ Configuration is valid")
    
    # Create necessary directories
    directories = [
        Path(config.output_dir),
        Path("backup"),
        Path("tests")
    ]
    
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")
    
    # Check git repository
    git_manager = GitManager(config)
    if git_manager.is_git_repository():
        print("✓ Git repository detected")
        
        # Get git info
        git_info = git_manager.get_git_info()
        print(f"   Branch: {git_info['current_branch']}")
        print(f"   Remote: {git_info['remote_url']}")
        
        if git_info['has_uncommitted_changes']:
            print("⚠️  Warning: Repository has uncommitted changes")
    else:
        print("❌ Not a git repository - some features will not work")
    
    print("\n✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Review and customize config.json if needed")
    print("2. Test with: python -m src.no_dust.main_processor <tag>")
    print("3. Run pipeline: python -m src.no_dust.pipeline_automation --single-run")
    
    return True


def check_status():
    """Check the current status of the no dust system."""
    print("Checking no dust system status...")
    
    try:
        config = Config.load_from_file("config.json")
        tracker = VersionTracker(config)
        git_manager = GitManager(config)
        
        # Get tracking status
        status = tracker.get_tracking_status()
        
        print(f"\n📊 System Status:")
        print(f"   Last version: {status['last_version']}")
        print(f"   Last SHA: {status['last_sha'][:12]}..." if status['last_sha'] else "   Last SHA: None")
        print(f"   Current SHA: {status['current_sha'][:12]}..." if status['current_sha'] else "   Current SHA: None")
        print(f"   Has changes: {status['has_changes']}")
        print(f"   Src exists: {status['src_exists']}")
        
        # Get git status
        git_info = git_manager.get_git_info()
        print(f"\n🔧 Git Status:")
        print(f"   Is git repo: {git_info['is_git_repo']}")
        print(f"   Current branch: {git_info['current_branch']}")
        print(f"   Has uncommitted changes: {git_info['has_uncommitted_changes']}")
        print(f"   Last commit: {git_info['last_commit']}")
        
        # Check output directory
        output_dir = Path(config.output_dir)
        if output_dir.exists():
            mod_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("no_dust")]
            print(f"\n📁 Output Status:")
            print(f"   Output directory: {output_dir}")
            print(f"   Mod directories: {len(mod_dirs)}")
            for mod_dir in sorted(mod_dirs)[:10]:  # Show first 10
                print(f"     - {mod_dir.name}")
            if len(mod_dirs) > 10:
                print(f"     ... and {len(mod_dirs) - 10} more")
        else:
            print(f"\n📁 Output Status:")
            print(f"   Output directory: {output_dir} (does not exist)")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False
    
    return True


def reset_system():
    """Reset the no dust system (useful for testing)."""
    print("Resetting no dust system...")
    
    try:
        config = Config.load_from_file("config.json")
        tracker = VersionTracker(config)
        
        # Reset tracking files
        if tracker.reset_tracking():
            print("✓ Reset tracking files")
        else:
            print("❌ Failed to reset tracking files")
        
        # Clean up temporary directories
        temp_dirs = [
            Path(config.temp_dir),
            Path(config.source_data_dir)
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                print(f"✓ Cleaned up: {temp_dir}")
        
        print("✅ System reset completed")
        
    except Exception as e:
        print(f"❌ Error resetting system: {e}")
        return False
    
    return True


def run_tests():
    """Run the test suite."""
    print("Running test suite...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed")
            return False
            
    except ImportError:
        print("❌ pytest not installed. Install with: pip install pytest")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def main():
    """Main setup script function."""
    parser = argparse.ArgumentParser(
        description="Setup and management script for CDDA No Dust"
    )
    parser.add_argument(
        "command",
        choices=["setup", "status", "reset", "test"],
        help="Command to run"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run the requested command
    if args.command == "setup":
        success = setup_system()
    elif args.command == "status":
        success = check_status()
    elif args.command == "reset":
        success = reset_system()
    elif args.command == "test":
        success = run_tests()
    else:
        print(f"Unknown command: {args.command}")
        success = False
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
