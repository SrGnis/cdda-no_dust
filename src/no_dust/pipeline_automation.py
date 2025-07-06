#!/usr/bin/env python3
"""
Pipeline Script for CDDA No Dust

This script handles the complete processing pipeline:
1. Checks for new tags in the source repository
2. Processes new tags using the main processor
3. Monitors changes to the src/ folder
4. Commits, pushes, and tags changes when detected
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Tuple

# Add the no_dust directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from main_processor import MainProcessor
from version_tracker import VersionTracker
from git_manager import GitManager
from utils import get_git_tags, compare_versions, add_common_arguments, setup_common_logging_and_config


class PipelineAutomation:
    """Main pipeline automation class."""
    
    def __init__(self, config: Config):
        """Initialize the pipeline automation with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.processor = MainProcessor(config)
        self.version_tracker = VersionTracker(config)
        self.git_manager = GitManager(config)
        self.initial_version = None
    
    def run_pipeline(self) -> bool:
        """
        Run the complete automation pipeline once.

        This will:
        1. Check for new tags and process them all
        2. Commit and push changes for each tag processed
        3. Make a final commit to track the last version processed

        Returns:
            bool: True if pipeline completed successfully
        """
        try:
            self.logger.info("Starting pipeline automation...")

            # Get the initial version before processing
            self.initial_version = self.version_tracker.get_last_version()

            # Check for new tags and process them
            if not self._check_and_process_new_tags():
                self.logger.error("Failed to check and process new tags")
                return False

            self.logger.info("Pipeline automation completed successfully")
            return True

        except KeyboardInterrupt:
            self.logger.info("Pipeline automation interrupted by user")
            return True
        except Exception as e:
            self.logger.error(f"Error in pipeline automation: {e}")
            return False
    
    def _check_and_process_new_tags(self) -> bool:
        """
        Check for new tags and process them.

        Returns:
            bool: True if check and processing was successful
        """
        try:
            self.logger.info("Checking for new tags...")

            # Get available tags from the source repository
            available_tags = get_git_tags(self.config.source_repo_url, "cdda-experimental")

            if not available_tags:
                self.logger.warning("No tags found in source repository")
                return True

            # Get the last processed version
            last_version = self.version_tracker.get_last_version()
            self.logger.info(f"Last processed version: {last_version}")

            # Find new tags to process
            new_tags = self._find_new_tags(available_tags, last_version)

            if not new_tags:
                self.logger.info("No new tags to process")
                return True

            self.logger.info(f"Found {len(new_tags)} new tags to process: {new_tags}")

            # Process each new tag and handle changes immediately
            for tag in new_tags:
                if not self._process_tag_safely(tag):
                    self.logger.error(f"Failed to process tag: {tag}")
                    return False

                # Check for changes and commit/push after each tag
                if not self._monitor_and_handle_changes_for_tag(tag):
                    self.logger.error(f"Failed to handle changes for tag: {tag}")
                    return False

            # Make a final commit to track the last version processed
            # Only commit if tags were processed and the version actually changed
            if new_tags:
                last_version = self.version_tracker.get_last_version()
                self.logger.info(f"Checking final version tracking: initial={self.initial_version}, last={last_version}")
                
                if self.initial_version != last_version:
                    self.logger.info("Version changed, committing final tracking update")
                    if not self._commit_version_tracking(last_version):
                        self.logger.error("Failed to commit final version tracking")
                        return False
                else:
                    self.logger.info("Last version unchanged, skipping final commit")

            self.logger.debug("Completed processing all new tags")
            return True

        except Exception as e:
            self.logger.error(f"Error checking and processing new tags: {e}")
            return False
    
    def _find_new_tags(self, available_tags: List[str], last_version: str) -> List[str]:
        """
        Find new tags that need to be processed.
        
        Args:
            available_tags: List of all available tags
            last_version: Last processed version
            
        Returns:
            List[str]: List of new tags to process
        """
        if not last_version or last_version == "unknown":
            # If no last version, process only the latest tag
            return available_tags[:1] if available_tags else []
        
        new_tags = []
        for tag in available_tags:
            if compare_versions(tag, last_version) > 0:
                new_tags.append(tag)
        
        # Sort new tags to process oldest first
        return sorted(new_tags)
    
    def _process_tag_safely(self, tag: str) -> bool:
        """
        Process a tag safely with error handling and rollback.
        
        Args:
            tag: Tag to process
            
        Returns:
            bool: True if processing was successful
        """
        try:
            self.logger.info(f"Processing tag: {tag}")
            
            # Create a backup of the current state
            backup_created = self.version_tracker.create_backup()
            
            try:
                # Process the tag
                if not self.processor.process_tag(tag):
                    raise Exception(f"Failed to process tag: {tag}")
                
                self.logger.info(f"Successfully processed tag: {tag}")
                return True
                
            except Exception as e:
                # Restore from backup if processing failed
                if backup_created:
                    self.logger.warning(f"Processing failed, restoring backup: {e}")
                    self.version_tracker.restore_backup()
                raise e
                
        except Exception as e:
            self.logger.error(f"Error processing tag {tag}: {e}")
            return False
    
    def _monitor_and_handle_changes_for_tag(self, tag: str) -> bool:
        """
        Monitor changes to the src/ folder and handle them for a specific tag.

        Args:
            tag: The tag that was just processed

        Returns:
            bool: True if monitoring and handling was successful
        """
        try:
            self.logger.debug(f"Monitoring changes for tag: {tag}")

            # Calculate current hash of src/ folder
            current_hash = self.version_tracker.calculate_src_hash()
            last_hash = self.version_tracker.get_last_sha()

            if current_hash == last_hash:
                self.logger.debug("No changes detected in src/ folder")
                return True

            self.logger.info(f"Changes detected in src/ folder for tag: {tag}")

            # Update the last SHA
            self.version_tracker.update_last_sha(current_hash)

            # Handle the changes
            if not self._handle_src_changes(tag):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error monitoring and handling changes for tag {tag}: {e}")
            return False

    def _monitor_and_handle_changes(self) -> bool:
        """
        Monitor changes to the src/ folder and handle them.

        Returns:
            bool: True if monitoring and handling was successful
        """
        try:
            self.logger.debug("Monitoring changes...")

            # Calculate current hash of src/ folder
            current_hash = self.version_tracker.calculate_src_hash()
            last_hash = self.version_tracker.get_last_sha()

            if current_hash == last_hash:
                self.logger.debug("No changes detected in src/ folder")
                return True

            self.logger.info("Changes detected in src/ folder")

            # Get the current version for tagging
            current_version = self.version_tracker.get_last_version()

            if not current_version or current_version == "unknown":
                self.logger.error("Cannot handle changes: no current version available")
                return False
            
            # Update the last SHA
            self.version_tracker.update_last_sha(current_hash)

            # Handle the changes
            if not self._handle_src_changes(current_version):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error monitoring and handling changes: {e}")
            return False
    
    def _handle_src_changes(self, version: str) -> bool:
        """
        Handle changes to the src/ folder by committing, pushing, and tagging.

        Args:
            version: Current version string

        Returns:
            bool: True if handling was successful
        """
        try:
            self.logger.info(f"Handling src/ changes for version: {version}")

            # Stage changes
            if not self.git_manager.stage_changes():
                return False

            # Commit changes
            commit_message = f"Update no-dust mods for {version}"
            if not self.git_manager.commit_changes(commit_message):
                return False

            # Create tag
            tag_name = version
            tag_message = f"No-dust mods for CDDA {version}"
            if not self.git_manager.create_tag(tag_name, tag_message):
                return False

            # Push changes and tags
            if not self.git_manager.push_changes():
                return False

            if not self.git_manager.push_tags():
                return False

            self.logger.info(f"Successfully handled changes and created tag: {tag_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error handling src/ changes: {e}")
            return False

    def _commit_version_tracking(self, last_tag: str) -> bool:
        """
        Commit and push a final commit to track the last version processed.

        Args:
            last_tag: The last tag that was processed

        Returns:
            bool: True if commit was successful
        """
        try:
            self.logger.info(f"Committing version tracking for last processed tag: {last_tag}")

            # Check if there are any changes to commit (version files, etc.)
            if not self.git_manager.has_uncommitted_changes():
                self.logger.debug("No changes to commit for version tracking")
                return True

            # Stage changes
            if not self.git_manager.stage_changes():
                return False

            # Commit version tracking changes
            commit_message = f"Track last processed version: {last_tag}"
            if not self.git_manager.commit_changes(commit_message):
                return False

            # Push changes
            if not self.git_manager.push_changes():
                return False

            self.logger.info(f"Successfully committed version tracking for: {last_tag}")
            return True

        except Exception as e:
            self.logger.error(f"Error committing version tracking: {e}")
            return False


def main():
    """Main function to handle command line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the CDDA no-dust mod automation pipeline"
    )
    add_common_arguments(parser)

    args = parser.parse_args()

    try:
        # Setup logging and load configuration
        config, logger = setup_common_logging_and_config(args)

        # Create and run the pipeline
        pipeline = PipelineAutomation(config)

        success = pipeline.run_pipeline()
        
        if success:
            logger.info("Pipeline automation completed successfully!")
            return 0
        else:
            logger.error("Pipeline automation failed!")
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
