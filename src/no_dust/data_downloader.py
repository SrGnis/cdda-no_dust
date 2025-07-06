#!/usr/bin/env python3
"""
Data Downloader for CDDA No Dust Mod Automation

This module handles downloading data from the CDDA repository with optimized
sparse checkout to only download the required data folders.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
import logging

from config import Config


class DataDownloader:
    """Handles downloading data from the CDDA repository."""
    
    def __init__(self, config: Config):
        """Initialize the data downloader with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def download_tag_data(self, tag: str) -> bool:
        """
        Download data for a specific tag from the CDDA repository.
        
        This method uses git sparse-checkout to only download the data/json
        and data/mods folders, making the download much faster and smaller.
        
        Args:
            tag: The git tag to download
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            self.logger.info(f"Downloading data for tag: {tag}")
            
            # Clean up any existing temporary directories
            self._cleanup_existing_temp()
            
            # Create temporary directory
            temp_dir = Path(self.config.temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Clone with sparse checkout
            if not self._clone_repository(tag):
                return False
            
            # Set up sparse checkout for only the data folder
            if not self._setup_sparse_checkout():
                return False
            
            # Checkout the specific tag
            if not self._checkout_tag(tag):
                return False
            
            # Move data to source_data directory
            if not self._move_data_to_source():
                return False
            
            self.logger.info(f"Successfully downloaded data for tag: {tag}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading data for tag {tag}: {e}")
            return False
    
    def _cleanup_existing_temp(self) -> None:
        """Clean up any existing temporary directories."""
        temp_paths = [
            Path(self.config.temp_dir),
            Path(self.config.source_data_dir)
        ]
        
        for temp_path in temp_paths:
            if temp_path.exists():
                shutil.rmtree(temp_path)
                self.logger.debug(f"Cleaned up existing directory: {temp_path}")
    
    def _clone_repository(self, tag: str) -> bool:
        """
        Clone the repository with optimized settings.
        
        Args:
            tag: The git tag to clone
            
        Returns:
            bool: True if clone was successful
        """
        try:
            clone_args = [
                "git", "clone",
                "--depth", str(self.config.git_depth),
                "--branch", tag,
                "--no-checkout"
            ]
            
            if self.config.git_filter_blob:
                clone_args.extend(["--filter=blob:none"])
            
            clone_args.extend([
                self.config.source_repo_url,
                self.config.temp_dir
            ])
            
            self.logger.debug(f"Running: {' '.join(clone_args)}")
            result = subprocess.run(
                clone_args,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.debug("Repository cloned successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to clone repository: {e}")
            return False
    
    def _setup_sparse_checkout(self) -> bool:
        """
        Set up sparse checkout to only include the data folder.
        
        Returns:
            bool: True if sparse checkout was set up successfully
        """
        try:
            temp_dir = Path(self.config.temp_dir)
            
            # Initialize sparse checkout
            result = subprocess.run(
                ["git", "sparse-checkout", "init", "--cone"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Set sparse checkout to only include data folder
            result = subprocess.run(
                ["git", "sparse-checkout", "set", "data"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.debug("Sparse checkout configured successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to setup sparse checkout: {e.stderr}")
            return False
    
    def _checkout_tag(self, tag: str) -> bool:
        """
        Checkout the specific tag.
        
        Args:
            tag: The git tag to checkout
            
        Returns:
            bool: True if checkout was successful
        """
        try:
            temp_dir = Path(self.config.temp_dir)
            
            result = subprocess.run(
                ["git", "checkout", tag],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.debug(f"Checked out tag: {tag}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to checkout tag {tag}: {e.stderr}")
            return False
    
    def _move_data_to_source(self) -> bool:
        """
        Move the downloaded data to the source_data directory.
        
        Returns:
            bool: True if move was successful
        """
        try:
            temp_data_dir = Path(self.config.temp_dir) / "data"
            source_data_dir = Path(self.config.source_data_dir)
            
            if not temp_data_dir.exists():
                self.logger.error(f"Data directory not found: {temp_data_dir}")
                return False
            
            # Move the data directory
            shutil.move(str(temp_data_dir), str(source_data_dir))
            
            self.logger.debug(f"Moved data from {temp_data_dir} to {source_data_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move data to source directory: {e}")
            return False
    
    def verify_download(self) -> bool:
        """
        Verify that the download was successful by checking for required directories.
        
        Returns:
            bool: True if all required directories exist
        """
        source_data_dir = Path(self.config.source_data_dir)
        required_dirs = [
            source_data_dir / self.config.data_json_path.split('/')[-1],  # json
            source_data_dir / self.config.data_mods_path.split('/')[-1]   # mods
        ]
        
        for required_dir in required_dirs:
            if not required_dir.exists():
                self.logger.error(f"Required directory not found: {required_dir}")
                return False
        
        self.logger.info("Download verification successful")
        return True
    
    def get_available_mods(self) -> List[str]:
        """
        Get a list of available mods from the downloaded data.
        
        Returns:
            List[str]: List of mod directory names
        """
        mods_dir = Path(self.config.source_data_dir) / "mods"
        
        if not mods_dir.exists():
            self.logger.warning(f"Mods directory not found: {mods_dir}")
            return []
        
        mods = []
        for item in mods_dir.iterdir():
            if item.is_dir() and not self.config.is_mod_excluded(item.name):
                mods.append(item.name)
        
        self.logger.info(f"Found {len(mods)} available mods")
        return sorted(mods)
