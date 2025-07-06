#!/usr/bin/env python3
"""
Data Organizer for CDDA No Dust Mod Automation

This module handles organizing the downloaded data into the proper structure
for processing. It moves data/json to tmp/dda/ and individual mod folders
from data/mods/ to tmp/mods/.
"""

import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging

from config import Config
from utils import ensure_directories, copy_directory_contents


class DataOrganizer:
    """Handles organizing downloaded data into the proper structure for processing."""
    
    def __init__(self, config: Config):
        """Initialize the data organizer with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def organize_data(self) -> bool:
        """
        Organize the downloaded data into the proper structure.
        
        This method:
        1. Creates the organized data directories
        2. Moves data/json to tmp/dda/
        3. Moves individual mod folders from data/mods/ to tmp/mods/
        
        Returns:
            bool: True if organization was successful, False otherwise
        """
        try:
            self.logger.info("Starting data organization...")
            
            # Create organized data directories
            if not self._create_organized_directories():
                return False
            
            # Organize main CDDA data
            if not self._organize_main_data():
                return False
            
            # Organize mod data
            if not self._organize_mod_data():
                return False
            
            self.logger.info("Data organization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error organizing data: {e}")
            return False
    
    def _create_organized_directories(self) -> bool:
        """
        Create the directories for organized data.

        Returns:
            bool: True if directories were created successfully
        """
        directories = [
            self.config.organized_main_data,
            self.config.organized_mods_data
        ]

        return ensure_directories(directories, self.logger)
    
    def _organize_main_data(self) -> bool:
        """
        Organize the main CDDA data (data/json) into tmp/dda/.
        
        Returns:
            bool: True if main data was organized successfully
        """
        try:
            source_json_dir = Path(self.config.source_data_dir) / "json"
            target_dda_dir = Path(self.config.organized_main_data)
            
            if not source_json_dir.exists():
                self.logger.error(f"Source JSON directory not found: {source_json_dir}")
                return False
            
            # Copy the entire json directory structure to tmp/dda/
            copy_directory_contents(source_json_dir, target_dda_dir, self.logger)
            
            self.logger.info(f"Organized main CDDA data: {source_json_dir} -> {target_dda_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize main data: {e}")
            return False
    
    def _organize_mod_data(self) -> bool:
        """
        Organize individual mod data from data/mods/ into tmp/mods/.
        
        Returns:
            bool: True if mod data was organized successfully
        """
        try:
            source_mods_dir = Path(self.config.source_data_dir) / "mods"
            target_mods_dir = Path(self.config.organized_mods_data)
            
            if not source_mods_dir.exists():
                self.logger.error(f"Source mods directory not found: {source_mods_dir}")
                return False
            
            organized_count = 0
            
            # Process each mod directory
            for mod_dir in source_mods_dir.iterdir():
                if not mod_dir.is_dir():
                    continue
                
                mod_name = mod_dir.name
                
                # Skip excluded mods
                if self.config.is_mod_excluded(mod_name):
                    self.logger.debug(f"Skipping excluded mod: {mod_name}")
                    continue
                
                # Create target directory for this mod
                target_mod_dir = target_mods_dir / mod_name
                target_mod_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy mod contents
                copy_directory_contents(mod_dir, target_mod_dir, self.logger)
                
                self.logger.debug(f"Organized mod: {mod_name}")
                organized_count += 1
            
            self.logger.info(f"Organized {organized_count} mods from {source_mods_dir} to {target_mods_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize mod data: {e}")
            return False
    

    
    def get_organized_mod_list(self) -> List[str]:
        """
        Get a list of organized mods.
        
        Returns:
            List[str]: List of mod names that were organized
        """
        organized_mods_dir = Path(self.config.organized_mods_data)
        
        if not organized_mods_dir.exists():
            return []
        
        mods = []
        for mod_dir in organized_mods_dir.iterdir():
            if mod_dir.is_dir():
                mods.append(mod_dir.name)
        
        return sorted(mods)
    
    def get_mod_info(self, mod_name: str) -> Optional[Dict]:
        """
        Get mod information from the modinfo.json file.
        
        Args:
            mod_name: Name of the mod
            
        Returns:
            Optional[Dict]: Mod information dictionary, or None if not found
        """
        mod_dir = Path(self.config.organized_mods_data) / mod_name
        modinfo_file = mod_dir / "modinfo.json"
        
        if not modinfo_file.exists():
            self.logger.warning(f"modinfo.json not found for mod: {mod_name}")
            return None
        
        try:
            import json
            with open(modinfo_file, 'r', encoding='utf-8') as f:
                modinfo_data = json.load(f)
            
            # Handle both single objects and arrays
            if isinstance(modinfo_data, list) and len(modinfo_data) > 0:
                return modinfo_data[0]  # Take the first mod info
            elif isinstance(modinfo_data, dict):
                return modinfo_data
            else:
                self.logger.warning(f"Invalid modinfo.json format for mod: {mod_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to read modinfo.json for mod {mod_name}: {e}")
            return None
    
    def verify_organization(self) -> bool:
        """
        Verify that the data organization was successful.
        
        Returns:
            bool: True if organization is valid
        """
        try:
            # Check that main data directory exists and has content
            main_data_dir = Path(self.config.organized_main_data)
            if not main_data_dir.exists() or not any(main_data_dir.iterdir()):
                self.logger.error(f"Main data directory is empty or missing: {main_data_dir}")
                return False
            
            # Check that mods directory exists
            mods_data_dir = Path(self.config.organized_mods_data)
            if not mods_data_dir.exists():
                self.logger.error(f"Mods data directory missing: {mods_data_dir}")
                return False
            
            # Count organized mods
            organized_mods = self.get_organized_mod_list()
            self.logger.info(f"Organization verification: {len(organized_mods)} mods organized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify organization: {e}")
            return False
    
    def cleanup_organized_data(self) -> None:
        """Clean up organized data directories."""
        try:
            directories = [
                Path(self.config.organized_main_data),
                Path(self.config.organized_mods_data)
            ]
            
            for directory in directories:
                if directory.exists():
                    shutil.rmtree(directory)
                    self.logger.debug(f"Cleaned up organized directory: {directory}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to cleanup some organized directories: {e}")
