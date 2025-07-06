#!/usr/bin/env python3
"""
Mod Processor for CDDA No Dust Mod Automation

This module handles processing the organized data to create no-dust mods.
It processes the main CDDA data and creates separate mod-specific folders
with customized modinfo.json files.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

from config import Config
from data_organizer import DataOrganizer
from utils import write_json_safe, read_json_safe


class ModProcessor:
    """Handles processing organized data to create no-dust mods."""
    
    def __init__(self, config: Config):
        """Initialize the mod processor with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.organizer = DataOrganizer(config)
    
    def process_main_data(self) -> bool:
        """
        Process the main CDDA data and output to src/no_dust/.
        
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            self.logger.info("Processing main CDDA data...")
            
            main_data_dir = Path(self.config.organized_main_data)
            output_dir = Path(self.config.main_output_dir)
            
            if not main_data_dir.exists():
                self.logger.error(f"Main data directory not found: {main_data_dir}")
                return False
            
            # Process the main data using the existing disable_dust.py logic
            if not self._process_data_directory(main_data_dir, output_dir):
                return False
            
            # Copy the base modinfo.json to the output directory
            if not self._copy_base_modinfo(output_dir):
                return False
            
            self.logger.info(f"Successfully processed main CDDA data to: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing main data: {e}")
            return False
    
    def process_mods(self) -> bool:
        """
        Process individual mods and create separate output folders.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            self.logger.info("Processing individual mods...")

            organized_mods = self.organizer.get_organized_mod_list()
            processed_count = 0
            empty_mods_cleaned = 0

            for mod_name in organized_mods:
                if self._process_single_mod(mod_name):
                    processed_count += 1
                    # Check if the processed mod is empty and clean it up
                    if self._is_mod_empty(mod_name) and self._cleanup_empty_mod(mod_name):
                        empty_mods_cleaned += 1
                else:
                    self.logger.warning(f"Failed to process mod: {mod_name}")

            if empty_mods_cleaned > 0:
                self.logger.info(f"Cleaned up {empty_mods_cleaned} empty mod directories")

            self.logger.info(f"Successfully processed {processed_count}/{len(organized_mods)} mods")
            return processed_count > 0 or len(organized_mods) == 0

        except Exception as e:
            self.logger.error(f"Error processing mods: {e}")
            return False
    
    def _process_single_mod(self, mod_name: str) -> bool:
        """
        Process a single mod and create its output folder.
        
        Args:
            mod_name: Name of the mod to process
            
        Returns:
            bool: True if processing was successful
        """
        try:
            self.logger.debug(f"Processing mod: {mod_name}")
            
            mod_data_dir = Path(self.config.organized_mods_data) / mod_name
            mod_output_dir = Path(self.config.get_mod_output_dir(mod_name))
            
            if not mod_data_dir.exists():
                self.logger.error(f"Mod data directory not found: {mod_data_dir}")
                return False
            
            # Process the mod data
            if not self._process_data_directory(mod_data_dir, mod_output_dir):
                return False
            
            # Create customized modinfo.json for this mod
            if not self._create_mod_modinfo(mod_name, mod_output_dir):
                return False
            
            self.logger.debug(f"Successfully processed mod: {mod_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing mod {mod_name}: {e}")
            return False
    
    def _process_data_directory(self, input_dir: Path, output_dir: Path) -> bool:
        """
        Process a data directory recursively.
        
        Args:
            input_dir: Input directory containing JSON files
            output_dir: Output directory for processed files
            
        Returns:
            bool: True if processing was successful
        """
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            processed_count = 0
            total_count = 0
            
            # Process all JSON files recursively
            for json_file in input_dir.rglob("*.json"):
                total_count += 1
                
                # Calculate relative path to maintain folder structure
                relative_path = json_file.relative_to(input_dir)
                output_file = output_dir / relative_path
                
                if self._process_json_file(json_file, output_file):
                    processed_count += 1
            
            self.logger.debug(f"Processed {processed_count}/{total_count} JSON files in {input_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing data directory {input_dir}: {e}")
            return False
    
    def _process_json_file(self, input_path: Path, output_path: Path) -> bool:
        """
        Process a single JSON file (adapted from disable_dust.py).
        
        Args:
            input_path: Path to the input JSON file
            output_path: Path to the output JSON file
            
        Returns:
            bool: True if file was processed and output created, False otherwise
        """
        try:
            data = read_json_safe(input_path, logger=self.logger)
            if data is None:
                return False

            # Handle both single objects and arrays
            if isinstance(data, list):
                processed_objects = []
                for item in data:
                    if isinstance(item, dict):
                        processed = self._process_json_object(item)
                        if processed:
                            processed_objects.append(processed)

                if processed_objects:
                    return write_json_safe(output_path, processed_objects, self.logger)

            elif isinstance(data, dict):
                processed = self._process_json_object(data)
                if processed:
                    return write_json_safe(output_path, processed, self.logger)

            return False

        except Exception as e:
            self.logger.debug(f"Error processing {input_path}: {e}")
            return False
    
    def _process_json_object(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON object (adapted from disable_dust.py).

        Uses copy-from but explicitly copies problematic fields that don't inherit
        properly due to CDDA inheritance bugs in mapdata.cpp.

        Args:
            obj: The JSON object to process

        Returns:
            Optional[Dict]: Processed object in the required format, or None if no target fields
        """
        if not self._has_target_fields(obj):
            return None

        # Extract the base information
        result = {}

        # Copy required fields
        if "type" in obj:
            result["type"] = obj["type"]
        if "id" in obj:
            result["id"] = obj["id"]
            result["copy-from"] = obj["id"]

        # Copy problematic fields that get lost due to CDDA inheritance bugs
        # These fields don't inherit properly with copy-from due to bugs in mapdata.cpp
        self._copy_inheritance_problematic_fields(obj, result)

        # Extract and process fields with hit_field or destroyed_field
        processed_fields = self._extract_and_zero_fields(obj)
        if processed_fields:
            result.update(processed_fields)

        return result

    def _copy_inheritance_problematic_fields(self, source: Dict[str, Any], target: Dict[str, Any]) -> None:
        """
        Copy fields that don't inherit properly with copy-from due to CDDA bugs.

        These fields have inheritance issues in CDDA's mapdata.cpp:
        - open/close properties (lines 1152-1154: was_loaded = false)
        - Activity data: prying, oxytorch, boltcut, hacksaw (lines 1160-1178: unconditional overwrite)

        Args:
            source: Source object to copy fields from
            target: Target object to copy fields to
        """
        # Door functionality fields (critical for doors to work)
        if "open" in source:
            target["open"] = source["open"]
        if "close" in source:
            target["close"] = source["close"]
        if "transforms_into" in source:
            target["transforms_into"] = source["transforms_into"]
        if "looks_like" in source:
            target["looks_like"] = source["looks_like"]

        # Activity data fields (get overwritten unconditionally in CDDA)
        if "prying" in source:
            target["prying"] = source["prying"]
        if "oxytorch" in source:
            target["oxytorch"] = source["oxytorch"]
        if "boltcut" in source:
            target["boltcut"] = source["boltcut"]
        if "hacksaw" in source:
            target["hacksaw"] = source["hacksaw"]

    def _has_target_fields(self, obj: Any) -> bool:
        """
        Recursively check if an object contains hit_field or destroyed_field.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if target fields are found
        """
        if isinstance(obj, dict):
            if "hit_field" in obj or "destroyed_field" in obj:
                return True
            for value in obj.values():
                if self._has_target_fields(value):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._has_target_fields(item):
                    return True
        
        return False
    
    def _extract_and_zero_fields(self, obj: Any) -> Optional[Dict[str, Any]]:
        """
        Extract relevant parts of an object and set field values to 0.
        
        Args:
            obj: The object to process
            
        Returns:
            Optional[Dict]: Processed object with zeroed fields, or None if no fields found
        """
        if not isinstance(obj, dict):
            return None
        
        result = {}
        found_fields = False
        
        for key, value in obj.items():
            if isinstance(value, dict):
                nested_result = self._extract_and_zero_fields(value)
                if nested_result:
                    result[key] = nested_result
                    found_fields = True
            elif key in ["hit_field", "destroyed_field"]:
                if isinstance(value, list) and len(value) >= 2:
                    result[key] = [value[0], 0]
                    found_fields = True
        
        return result if found_fields else None

    def _copy_base_modinfo(self, output_dir: Path) -> bool:
        """
        Copy the base modinfo.json to the output directory.

        Args:
            output_dir: Output directory where to copy the modinfo.json

        Returns:
            bool: True if copy was successful
        """
        try:
            base_modinfo_path = Path(self.config.main_output_dir) / "modinfo.json"
            target_modinfo_path = output_dir / "modinfo.json"

            # If the base modinfo exists, copy it
            if base_modinfo_path.exists() and base_modinfo_path != target_modinfo_path:
                shutil.copy2(base_modinfo_path, target_modinfo_path)
                self.logger.debug(f"Copied base modinfo.json to {target_modinfo_path}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to copy base modinfo.json: {e}")
            return False

    def _create_mod_modinfo(self, mod_name: str, output_dir: Path) -> bool:
        """
        Create a customized modinfo.json for a specific mod.

        Args:
            mod_name: Name of the mod
            output_dir: Output directory where to create the modinfo.json

        Returns:
            bool: True if creation was successful
        """
        try:
            # Get original mod info
            original_mod_info = self.organizer.get_mod_info(mod_name)
            if not original_mod_info:
                self.logger.warning(f"Could not get mod info for {mod_name}, using default")
                mod_display_name = mod_name.replace('_', ' ').title()
                original_mod_id = mod_name.lower()
            else:
                mod_display_name = original_mod_info.get('name', mod_name)
                original_mod_id = original_mod_info.get('id', mod_name.lower())

            # Get current version from last_version file
            version = self._get_current_version()

            # Create customized modinfo with correct dependency ID
            mod_template = self._create_custom_mod_template(
                mod_display_name, original_mod_id, version
            )

            # Save to output directory
            modinfo_path = output_dir / "modinfo.json"
            modinfo_path.parent.mkdir(parents=True, exist_ok=True)

            with open(modinfo_path, 'w', encoding='utf-8') as f:
                json.dump([mod_template], f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Created modinfo.json for mod: {mod_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create modinfo.json for mod {mod_name}: {e}")
            return False

    def _create_custom_mod_template(self, mod_display_name: str,
                                   original_mod_id: str, version: str) -> Dict[str, Any]:
        """
        Create a custom mod template with the correct dependency ID.

        Args:
            mod_display_name: Display name for the mod
            original_mod_id: Original mod ID from the source modinfo.json
            version: Version string to include

        Returns:
            Dict: Custom mod template with correct dependencies
        """
        # Create the base template
        template = {
            "type": "MOD_INFO",
            "id": f"no_dust_{original_mod_id}",
            "name": f"No Dust - {mod_display_name}",
            "authors": ["SrGnis"],
            "description": f"Prevents dust from being generated in {mod_display_name}.",
            "category": "item_exclude",
            "dependencies": ["dda", original_mod_id],
            "core": False,
            "obsolete": False,
            "version": version
        }

        return template

    def _get_current_version(self) -> str:
        """
        Get the current version from the last_version file.

        Returns:
            str: Current version string
        """
        try:
            version_file = Path(self.config.last_version_file)
            if version_file.exists():
                return version_file.read_text().strip()
            else:
                return "unknown"
        except Exception:
            return "unknown"

    def _is_mod_empty(self, mod_name: str) -> bool:
        """
        Check if a processed mod directory is empty (contains only modinfo.json).

        Args:
            mod_name: Name of the mod to check

        Returns:
            bool: True if the mod directory is empty (only contains modinfo.json)
        """
        try:
            mod_output_dir = Path(self.config.get_mod_output_dir(mod_name))

            if not mod_output_dir.exists():
                return True

            # Get all files in the mod directory
            all_files = list(mod_output_dir.rglob("*"))
            files_only = [f for f in all_files if f.is_file()]

            # If there's only modinfo.json or no files at all, consider it empty
            if len(files_only) == 0:
                return True
            elif len(files_only) == 1 and files_only[0].name == "modinfo.json":
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error checking if mod {mod_name} is empty: {e}")
            return False

    def _cleanup_empty_mod(self, mod_name: str) -> bool:
        """
        Remove an empty mod directory.

        Args:
            mod_name: Name of the mod to clean up

        Returns:
            bool: True if cleanup was successful
        """
        try:
            mod_output_dir = Path(self.config.get_mod_output_dir(mod_name))

            if mod_output_dir.exists():
                shutil.rmtree(mod_output_dir)
                self.logger.info(f"Cleaned up empty mod directory: {mod_output_dir}")
                return True

            return True

        except Exception as e:
            self.logger.error(f"Error cleaning up empty mod {mod_name}: {e}")
            return False
