#!/usr/bin/env python3
"""
Version and Change Tracking for CDDA No Dust Mod Automation

This module handles tracking the last processed version, calculating SHA hashes
of the src/ folder, and detecting changes for the automation system.
"""

import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from config import Config
from utils import calculate_folder_hash, read_file_safe, write_file_safe


class VersionTracker:
    """Handles version and change tracking for the automation system."""
    
    def __init__(self, config: Config):
        """Initialize the version tracker with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.backup_dir = Path("backup")
    
    def get_last_version(self) -> str:
        """
        Get the last processed version.
        
        Returns:
            str: Last processed version or "unknown" if not found
        """
        return read_file_safe(Path(self.config.last_version_file), "unknown")
    
    def update_last_version(self, version: str) -> bool:
        """
        Update the last processed version.
        
        Args:
            version: Version string to save
            
        Returns:
            bool: True if update was successful
        """
        success = write_file_safe(Path(self.config.last_version_file), version)
        if success:
            self.logger.info(f"Updated last version to: {version}")
        else:
            self.logger.error(f"Failed to update last version to: {version}")
        return success
    
    def get_last_sha(self) -> str:
        """
        Get the last SHA hash of the src/ folder.
        
        Returns:
            str: Last SHA hash or empty string if not found
        """
        return read_file_safe(Path(self.config.last_sha_file), "")
    
    def update_last_sha(self, sha_hash: str) -> bool:
        """
        Update the last SHA hash of the src/ folder.
        
        Args:
            sha_hash: SHA hash to save
            
        Returns:
            bool: True if update was successful
        """
        success = write_file_safe(Path(self.config.last_sha_file), sha_hash)
        if success:
            self.logger.info(f"Updated last SHA to: {sha_hash[:12]}...")
        else:
            self.logger.error(f"Failed to update last SHA")
        return success
    
    def calculate_src_hash(self) -> str:
        """
        Calculate the current SHA hash of the src/ folder.
        
        Returns:
            str: SHA hash of the src/ folder contents
        """
        src_dir = Path(self.config.output_dir)
        
        # Exclude patterns for files that shouldn't affect the hash
        exclude_patterns = [
            '.git',
            '__pycache__',
            '*.pyc',
            '.DS_Store',
            'Thumbs.db',
            '*.log',
            'modinfo.json'
        ]
        
        hash_value = calculate_folder_hash(src_dir, exclude_patterns)
        self.logger.debug(f"Calculated src/ hash: {hash_value[:12]}...")
        return hash_value
    
    def has_src_changed(self) -> bool:
        """
        Check if the src/ folder has changed since the last check.
        
        Returns:
            bool: True if src/ folder has changed
        """
        current_hash = self.calculate_src_hash()
        last_hash = self.get_last_sha()
        
        changed = current_hash != last_hash
        if changed:
            self.logger.info("Changes detected in src/ folder")
        else:
            self.logger.debug("No changes detected in src/ folder")
        
        return changed
    
    def create_backup(self) -> bool:
        """
        Create a backup of the current state (version files and src/ folder).
        
        Returns:
            bool: True if backup was created successfully
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup version files
            version_file = Path(self.config.last_version_file)
            sha_file = Path(self.config.last_sha_file)
            
            if version_file.exists():
                shutil.copy2(version_file, backup_path / "last_version")
            
            if sha_file.exists():
                shutil.copy2(sha_file, backup_path / "last_sha")
            
            # Backup src/ folder if it exists
            src_dir = Path(self.config.output_dir)
            if src_dir.exists():
                backup_src_dir = backup_path / "src"
                shutil.copytree(src_dir, backup_src_dir, dirs_exist_ok=True)
            
            # Create backup metadata
            metadata = {
                "timestamp": timestamp,
                "version": self.get_last_version(),
                "sha": self.get_last_sha(),
                "created_at": datetime.now().isoformat()
            }
            
            metadata_file = backup_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False
    
    def restore_backup(self, backup_name: Optional[str] = None) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_name: Name of the backup to restore (None for latest)
            
        Returns:
            bool: True if restore was successful
        """
        try:
            if backup_name:
                backup_path = self.backup_dir / backup_name
            else:
                # Find the latest backup
                backup_path = self._find_latest_backup()
            
            if not backup_path or not backup_path.exists():
                self.logger.error("No backup found to restore")
                return False
            
            self.logger.info(f"Restoring from backup: {backup_path}")
            
            # Restore version files
            backup_version_file = backup_path / "last_version"
            backup_sha_file = backup_path / "last_sha"
            
            if backup_version_file.exists():
                shutil.copy2(backup_version_file, self.config.last_version_file)
            
            if backup_sha_file.exists():
                shutil.copy2(backup_sha_file, self.config.last_sha_file)
            
            # Restore src/ folder
            backup_src_dir = backup_path / "src"
            src_dir = Path(self.config.output_dir)
            
            if backup_src_dir.exists():
                # Remove current src/ folder
                if src_dir.exists():
                    shutil.rmtree(src_dir)
                
                # Restore from backup
                shutil.copytree(backup_src_dir, src_dir)
            
            self.logger.info("Backup restored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _find_latest_backup(self) -> Optional[Path]:
        """
        Find the latest backup directory.
        
        Returns:
            Optional[Path]: Path to the latest backup or None if not found
        """
        if not self.backup_dir.exists():
            return None
        
        backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")]
        
        if not backup_dirs:
            return None
        
        # Sort by name (which includes timestamp) and return the latest
        return sorted(backup_dirs)[-1]
    
    def cleanup_old_backups(self, keep_count: int = 5) -> None:
        """
        Clean up old backups, keeping only the specified number.
        
        Args:
            keep_count: Number of backups to keep
        """
        try:
            if not self.backup_dir.exists():
                return
            
            backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")]
            
            if len(backup_dirs) <= keep_count:
                return
            
            # Sort by name (timestamp) and remove oldest
            sorted_backups = sorted(backup_dirs)
            backups_to_remove = sorted_backups[:-keep_count]
            
            for backup_dir in backups_to_remove:
                shutil.rmtree(backup_dir)
                self.logger.debug(f"Removed old backup: {backup_dir}")
            
            self.logger.info(f"Cleaned up {len(backups_to_remove)} old backups")
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")
    
    def get_tracking_status(self) -> Dict[str, Any]:
        """
        Get the current tracking status.
        
        Returns:
            Dict[str, Any]: Dictionary containing tracking status information
        """
        return {
            "last_version": self.get_last_version(),
            "last_sha": self.get_last_sha(),
            "current_sha": self.calculate_src_hash(),
            "has_changes": self.has_src_changed(),
            "src_exists": Path(self.config.output_dir).exists(),
            "version_file_exists": Path(self.config.last_version_file).exists(),
            "sha_file_exists": Path(self.config.last_sha_file).exists()
        }
    
    def reset_tracking(self) -> bool:
        """
        Reset all tracking files (useful for testing or manual reset).
        
        Returns:
            bool: True if reset was successful
        """
        try:
            files_to_remove = [
                Path(self.config.last_version_file),
                Path(self.config.last_sha_file)
            ]
            
            for file_path in files_to_remove:
                if file_path.exists():
                    file_path.unlink()
                    self.logger.debug(f"Removed tracking file: {file_path}")
            
            self.logger.info("Tracking files reset successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset tracking files: {e}")
            return False
