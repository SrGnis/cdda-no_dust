#!/usr/bin/env python3
"""
Utility functions for CDDA No Dust Mod Automation

This module contains common utility functions used throughout the automation system.
"""

import hashlib
import logging
import sys
import json
import argparse
import shutil
from pathlib import Path
from typing import Optional, List, Union, Dict, Any
import subprocess


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration for the automation system.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def setup_logging_from_config(config) -> None:
    """
    Set up logging using configuration object.

    Args:
        config: Config object with log_level and log_file attributes
    """
    setup_logging(config.log_level, config.log_file)


def calculate_folder_hash(folder_path: Path, exclude_patterns: Optional[List[str]] = None) -> str:
    """
    Calculate a SHA256 hash of all files in a folder.
    
    Args:
        folder_path: Path to the folder to hash
        exclude_patterns: List of patterns to exclude from hashing
        
    Returns:
        str: SHA256 hash of the folder contents
    """
    if exclude_patterns is None:
        exclude_patterns = ['.git', '__pycache__', '*.pyc', '.DS_Store']
    
    hash_sha256 = hashlib.sha256()
    
    if not folder_path.exists():
        return ""
    
    # Get all files in the folder, sorted for consistent hashing
    all_files = []
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            # Check if file should be excluded
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in str(file_path):
                    should_exclude = True
                    break
            
            if not should_exclude:
                all_files.append(file_path)
    
    # Sort files for consistent hashing
    all_files.sort()
    
    # Hash each file's content and path
    for file_path in all_files:
        try:
            # Add relative path to hash
            relative_path = file_path.relative_to(folder_path)
            hash_sha256.update(str(relative_path).encode('utf-8'))
            
            # Add file content to hash
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
                    
        except (IOError, OSError):
            # Skip files that can't be read
            continue
    
    return hash_sha256.hexdigest()


def read_file_safe(file_path: Path, default: str = "") -> str:
    """
    Safely read a file and return its content or a default value.
    
    Args:
        file_path: Path to the file to read
        default: Default value to return if file can't be read
        
    Returns:
        str: File content or default value
    """
    try:
        if file_path.exists():
            return file_path.read_text().strip()
        else:
            return default
    except Exception:
        return default


def write_file_safe(file_path: Path, content: str) -> bool:
    """
    Safely write content to a file.

    Args:
        file_path: Path to the file to write
        content: Content to write

    Returns:
        bool: True if write was successful, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return True
    except Exception:
        return False


def ensure_directories(directories: List[Union[str, Path]], logger: Optional[logging.Logger] = None) -> bool:
    """
    Ensure multiple directories exist, creating them if necessary.

    Args:
        directories: List of directory paths to create
        logger: Optional logger for debug messages

    Returns:
        bool: True if all directories were created successfully
    """
    try:
        for directory in directories:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            if logger:
                logger.debug(f"Ensured directory exists: {dir_path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to create directories: {e}")
        return False


def write_json_safe(file_path: Path, data: Union[Dict[str, Any], List[Dict[str, Any]]], logger: Optional[logging.Logger] = None) -> bool:
    """
    Safely write JSON data to a file with consistent formatting.

    Args:
        file_path: Path to the JSON file
        data: Data to write as JSON
        logger: Optional logger for debug messages

    Returns:
        bool: True if write was successful
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if logger:
            logger.debug(f"Successfully wrote JSON file: {file_path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to write JSON file {file_path}: {e}")
        return False


def read_json_safe(file_path: Path, default: Optional[Union[Dict, List]] = None, logger: Optional[logging.Logger] = None) -> Union[Dict, List, None]:
    """
    Safely read JSON data from a file.

    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid
        logger: Optional logger for debug messages

    Returns:
        Parsed JSON data or default value
    """
    try:
        if not file_path.exists():
            if logger:
                logger.debug(f"JSON file does not exist: {file_path}")
            return default

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if logger:
            logger.debug(f"Successfully read JSON file: {file_path}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        if logger:
            logger.error(f"Failed to read JSON file {file_path}: {e}")
        return default


def run_command(command: List[str], cwd: Optional[Path] = None, capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Run a command and return the result.
    
    Args:
        command: Command to run as a list of strings
        cwd: Working directory for the command
        capture_output: Whether to capture stdout and stderr
        
    Returns:
        subprocess.CompletedProcess: Result of the command
    """
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        check=False
    )


def check_git_repository(repo_path: Path) -> bool:
    """
    Check if a directory is a git repository.
    
    Args:
        repo_path: Path to check
        
    Returns:
        bool: True if it's a git repository
    """
    try:
        result = run_command(["git", "rev-parse", "--git-dir"], cwd=repo_path)
        return result.returncode == 0
    except Exception:
        return False


def get_git_tags(repo_url: str, pattern: Optional[str] = None) -> List[str]:
    """
    Get a list of git tags from a remote repository.
    
    Args:
        repo_url: URL of the git repository
        pattern: Optional pattern to filter tags
        
    Returns:
        List[str]: List of git tags
    """
    try:
        command = ["git", "ls-remote", "--tags", repo_url]
        result = run_command(command)
        
        if result.returncode != 0:
            return []
        
        tags = []
        for line in result.stdout.strip().split('\n'):
            if line and 'refs/tags/' in line:
                tag = line.split('refs/tags/')[-1]
                # Remove ^{} suffix if present
                if tag.endswith('^{}'):
                    tag = tag[:-3]
                
                # Apply pattern filter if specified
                if pattern is None or pattern in tag:
                    tags.append(tag)
        
        return sorted(tags, reverse=True)  # Most recent first
        
    except Exception:
        return []


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.

    Args:
        version1: First version string
        version2: Second version string

    Returns:
        int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    # Simple string comparison for CDDA tags
    # This works for the CDDA tag format: cdda-experimental-YYYY-MM-DD-HHMM
    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    else:
        return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add common command-line arguments to an argument parser.

    Args:
        parser: ArgumentParser to add arguments to
    """
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )


def setup_common_logging_and_config(args) -> tuple:
    """
    Set up logging and load configuration from common arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (config, logger) - Config object and logger instance
    """
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    from config import Config  # Import here to avoid circular imports
    config = Config.load_from_file(args.config)

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError("Configuration validation failed")

    return config, logger


def cleanup_directories(directories: List[Union[str, Path]], logger: Optional[logging.Logger] = None) -> bool:
    """
    Clean up (remove) multiple directories safely.

    Args:
        directories: List of directory paths to remove
        logger: Optional logger for debug messages

    Returns:
        bool: True if all directories were cleaned up successfully
    """
    success = True
    for directory in directories:
        dir_path = Path(directory)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                if logger:
                    logger.debug(f"Cleaned up directory: {dir_path}")
            except Exception as e:
                if logger:
                    logger.error(f"Failed to clean up directory {dir_path}: {e}")
                success = False
        else:
            if logger:
                logger.debug(f"Directory does not exist (skipping): {dir_path}")

    return success


def copy_directory_contents(source_dir: Path, target_dir: Path, logger: Optional[logging.Logger] = None) -> bool:
    """
    Copy the contents of a source directory to a target directory.

    Args:
        source_dir: Source directory to copy from
        target_dir: Target directory to copy to
        logger: Optional logger for debug messages

    Returns:
        bool: True if copy was successful
    """
    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        for item in source_dir.iterdir():
            target_item = target_dir / item.name

            if item.is_dir():
                shutil.copytree(item, target_item, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target_item)

        if logger:
            logger.debug(f"Copied directory contents: {source_dir} -> {target_dir}")
        return True

    except Exception as e:
        if logger:
            logger.error(f"Failed to copy directory contents from {source_dir} to {target_dir}: {e}")
        return False


def ensure_directory(directory: Path) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure
        
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def clean_directory(directory: Path, keep_patterns: Optional[List[str]] = None) -> bool:
    """
    Clean a directory, optionally keeping files matching certain patterns.
    
    Args:
        directory: Directory to clean
        keep_patterns: List of patterns for files to keep
        
    Returns:
        bool: True if cleaning was successful
    """
    try:
        if not directory.exists():
            return True
        
        if keep_patterns is None:
            keep_patterns = []
        
        for item in directory.iterdir():
            should_keep = False
            for pattern in keep_patterns:
                if pattern in item.name:
                    should_keep = True
                    break
            
            if not should_keep:
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        return True
        
    except Exception:
        return False
