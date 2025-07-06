#!/usr/bin/env python3
"""
Main Processing Script for CDDA No Dust

This script handles the complete processing pipeline:
1. Downloads data from CDDA repository for a specific tag
2. Organizes data into proper folder structure
3. Processes main CDDA data and individual mods
4. Generates mod-specific output folders
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Add the no_dust directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_downloader import DataDownloader
from data_organizer import DataOrganizer
from mod_processor import ModProcessor
from version_tracker import VersionTracker
from config import Config
from utils import calculate_folder_hash, add_common_arguments, setup_common_logging_and_config


class MainProcessor:
    """Main processing class that orchestrates the entire pipeline."""
    
    def __init__(self, config: Config):
        """Initialize the main processor with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.downloader = DataDownloader(config)
        self.organizer = DataOrganizer(config)
        self.mod_processor = ModProcessor(config)
        self.version_tracker = VersionTracker(config)
    
    def process_tag(self, tag: str) -> bool:
        """
        Process a specific CDDA tag through the complete pipeline.
        
        Args:
            tag: The git tag to process (e.g., 'cdda-experimental-2025-07-04-0449')
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting processing for tag: {tag}")
            
            # Step 1: Download data for the specific tag
            self.logger.info("Step 1: Downloading data...")
            if not self.downloader.download_tag_data(tag):
                self.logger.error("Failed to download data")
                return False
            
            # Step 2: Organize downloaded data
            self.logger.info("Step 2: Organizing data...")
            if not self.organizer.organize_data():
                self.logger.error("Failed to organize data")
                return False
            
            # Step 3: Process main CDDA data
            self.logger.info("Step 3: Processing main CDDA data...")
            if not self.mod_processor.process_main_data():
                self.logger.error("Failed to process main CDDA data")
                return False
            
            # Step 4: Process individual mods
            self.logger.info("Step 4: Processing individual mods...")
            if not self.mod_processor.process_mods():
                self.logger.error("Failed to process mods")
                return False
            
            # Step 5: Update version tracking
            self.logger.info("Step 5: Updating version tracking...")
            if not self.version_tracker.update_last_version(tag):
                self.logger.error("Failed to update version tracking")
                return False

            self.logger.info("Processing completed successfully")
            
            self.logger.info(f"Successfully processed tag: {tag}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing tag {tag}: {e}")
            return False
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files()
    

    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files and directories."""
        if not self.config.cleanup_temp_files:
            self.logger.debug("Skipping cleanup of temporary files (cleanup disabled)")
            return

        try:
            temp_dirs = [
                Path(self.config.temp_dir),
                Path(self.config.source_data_dir)
            ]

            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")

        except Exception as e:
            self.logger.warning(f"Failed to cleanup some temporary files: {e}")


def main():
    """Main function to handle command line arguments and run the processor."""
    parser = argparse.ArgumentParser(
        description="Process CDDA data for a specific tag to create no-dust mods"
    )
    parser.add_argument(
        "tag",
        help="Git tag to process (e.g., 'cdda-experimental-2025-07-04-0449')"
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup temporary files after processing"
    )
    
    args = parser.parse_args()

    try:
        # Setup logging and load configuration
        config, logger = setup_common_logging_and_config(args)
        
        # Override cleanup setting if specified
        if args.no_cleanup:
            config.cleanup_temp_files = False
        
        # Create and run the processor
        processor = MainProcessor(config)
        success = processor.process_tag(args.tag)
        
        if success:
            logger.info("Processing completed successfully!")
            return 0
        else:
            logger.error("Processing failed!")
            return 1
            
    except ValueError as e:
        # Configuration validation error
        return 1
    except Exception as e:
        # Try to get a logger for error reporting
        try:
            logger = logging.getLogger(__name__)
            logger.error(f"Fatal error: {e}")
        except:
            print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
