#!/usr/bin/env python3
"""
CDDA No Dust Package

This package provides a comprehensive system for creating no-dust mods
for Cataclysm: Dark Days Ahead (CDDA) from the official repository data.

Main Components:
- main_processor: Core processing script that handles tag processing
- pipeline_automation: Main pipeline for continuous operation
- config: Configuration management
- data_downloader: Downloads data from CDDA repository
- data_organizer: Organizes downloaded data into proper structure
- mod_processor: Processes data to create no-dust mods
- version_tracker: Tracks versions and changes
- git_manager: Handles git operations
- utils: Common utility functions

Usage:
    # Process a specific tag
    python -m src.no_dust.main_processor cdda-experimental-2025-07-04-0449

    # Run the pipeline
    python -m src.no_dust.pipeline_automation --single-run

    # Run continuous processing
    python -m src.no_dust.pipeline_automation --check-interval 3600
"""

__version__ = "1.0.0"
__author__ = "SrGnis"
__email__ = "srgnis@srgnis.xyz"

# Import main classes for easy access
from .config import Config
from .main_processor import MainProcessor
from .pipeline_automation import PipelineAutomation
from .data_downloader import DataDownloader
from .data_organizer import DataOrganizer
from .mod_processor import ModProcessor
from .version_tracker import VersionTracker
from .git_manager import GitManager

__all__ = [
    "Config",
    "MainProcessor", 
    "PipelineAutomation",
    "DataDownloader",
    "DataOrganizer", 
    "ModProcessor",
    "VersionTracker",
    "GitManager"
]
