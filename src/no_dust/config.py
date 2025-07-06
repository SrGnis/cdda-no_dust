#!/usr/bin/env python3
"""
Configuration management for CDDA No Dust

This module handles loading and managing configuration settings for the no dust system.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Config:
    """Configuration class for the no dust system."""
    
    # Repository settings
    source_repo_url: str = "https://github.com/CleverRaven/Cataclysm-DDA.git"
    
    # Directory paths (relative to project root)
    project_root: str = "."
    temp_dir: str = "tmp"
    source_data_dir: str = "source_data"
    output_dir: str = "src/dist"
    
    # Specific output directories
    main_output_dir: str = "src/dist/no_dust"
    mod_output_prefix: str = "src/dist/no_dust_"
    
    # Data paths within the downloaded repository
    data_json_path: str = "data/json"
    data_mods_path: str = "data/mods"
    
    # Organized data paths
    organized_main_data: str = "tmp/dda"
    organized_mods_data: str = "tmp/mods"
    
    # Tracking files
    last_version_file: str = "last_version"
    last_sha_file: str = "last_sha"
    
    # Processing settings
    cleanup_temp_files: bool = True
    preserve_folder_structure: bool = True
    
    # Mod template settings
    mod_template: Dict[str, Any] = None
    
    # Git settings
    git_sparse_checkout: bool = True
    git_depth: int = 1
    git_filter_blob: bool = True
    
    # Excluded mods (mods to skip processing)
    excluded_mods: List[str] = None
    
    # Logging settings
    log_file: Optional[str] = "no_dust.log"
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Initialize default values that need to be computed."""
        if self.mod_template is None:
            self.mod_template = {
                "type": "MOD_INFO",
                "id": "no_dust_{mod_name}",
                "name": "No Dust - {mod_display_name}",
                "authors": ["SrGnis"],
                "description": "Prevents dust from being generated in {mod_display_name}.",
                "category": "item_exclude",
                "dependencies": ["dda", "{mod_name}"],
                "core": False,
                "obsolete": False
            }
        
        if self.excluded_mods is None:
            self.excluded_mods = [
                "dda",  # Base game, handled separately
                "TEST_DATA",  # Test data, not a real mod
                "default.json"  # Not a mod folder
            ]
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Config':
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Config: Loaded configuration object
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            # Create default configuration file
            default_config = cls()
            default_config.save_to_file(config_path)
            return default_config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Create config object with loaded data
            config = cls(**config_data)
            return config
            
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid configuration file {config_path}: {e}")
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            config_path: Path where to save the configuration file
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """
        Convert a relative path to an absolute path based on project root.
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            Path: Absolute path
        """
        return Path(self.project_root).resolve() / relative_path
    
    def get_mod_output_dir(self, mod_name: str) -> str:
        """
        Get the output directory for a specific mod.
        
        Args:
            mod_name: Name of the mod
            
        Returns:
            str: Output directory path for the mod
        """
        return f"{self.mod_output_prefix}{mod_name}"
    
    def get_mod_template_filled(self, mod_name: str, mod_display_name: str, version: str) -> Dict[str, Any]:
        """
        Get a filled mod template for a specific mod.
        
        Args:
            mod_name: Internal mod name (used for IDs)
            mod_display_name: Display name for the mod
            version: Version string to include
            
        Returns:
            Dict: Filled mod template
        """
        template = self.mod_template.copy()
        
        # Replace placeholders
        for key, value in template.items():
            if isinstance(value, str):
                template[key] = value.format(
                    mod_name=mod_name,
                    mod_display_name=mod_display_name,
                    version=version
                )
            elif isinstance(value, list):
                template[key] = [
                    item.format(mod_name=mod_name, mod_display_name=mod_display_name, version=version)
                    if isinstance(item, str) else item
                    for item in value
                ]
        
        # Add version
        template["version"] = version
        
        return template
    
    def is_mod_excluded(self, mod_name: str) -> bool:
        """
        Check if a mod should be excluded from processing.
        
        Args:
            mod_name: Name of the mod to check
            
        Returns:
            bool: True if the mod should be excluded
        """
        return mod_name in self.excluded_mods
    
    def validate(self) -> List[str]:
        """
        Validate the configuration and return any errors.
        
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required string fields
        required_fields = [
            'source_repo_url', 'project_root', 'temp_dir', 'source_data_dir',
            'output_dir', 'main_output_dir', 'data_json_path', 'data_mods_path'
        ]
        
        for field in required_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(f"Required field '{field}' is missing or invalid")
        
        # Check that mod_template is a dictionary
        if not isinstance(self.mod_template, dict):
            errors.append("mod_template must be a dictionary")
        
        # Check that excluded_mods is a list
        if not isinstance(self.excluded_mods, list):
            errors.append("excluded_mods must be a list")
        
        return errors
