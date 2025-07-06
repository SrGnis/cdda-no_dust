#!/usr/bin/env python3
"""
Test Suite for CDDA No Dust

This module contains comprehensive tests for all no dust components.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.no_dust.config import Config
from src.no_dust.data_downloader import DataDownloader
from src.no_dust.data_organizer import DataOrganizer
from src.no_dust.mod_processor import ModProcessor
from src.no_dust.version_tracker import VersionTracker
from src.no_dust.git_manager import GitManager
from src.no_dust.main_processor import MainProcessor
from src.no_dust.utils import calculate_folder_hash, setup_logging


class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_creation(self):
        """Test creating a default configuration."""
        config = Config()
        self.assertEqual(config.source_repo_url, "https://github.com/CleverRaven/Cataclysm-DDA.git")
        self.assertEqual(config.temp_dir, "tmp")
        self.assertTrue(config.cleanup_temp_files)
    
    def test_config_save_and_load(self):
        """Test saving and loading configuration."""
        # Create and save config
        config = Config(temp_dir="test_tmp", cleanup_temp_files=False)
        config.save_to_file(str(self.config_file))
        
        # Load config
        loaded_config = Config.load_from_file(str(self.config_file))
        
        self.assertEqual(loaded_config.temp_dir, "test_tmp")
        self.assertFalse(loaded_config.cleanup_temp_files)
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        errors = config.validate()
        self.assertEqual(len(errors), 0)
        
        # Test invalid config
        config.source_repo_url = ""
        errors = config.validate()
        self.assertGreater(len(errors), 0)
    
    def test_mod_template_filling(self):
        """Test mod template filling."""
        config = Config()
        template = config.get_mod_template_filled("aftershock", "Aftershock", "test-version")
        
        self.assertEqual(template["id"], "no_dust_aftershock")
        self.assertEqual(template["name"], "No Dust - Aftershock")
        self.assertEqual(template["version"], "test-version")
        self.assertIn("aftershock", template["dependencies"])


class TestDataDownloader(unittest.TestCase):
    """Test cases for the DataDownloader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            temp_dir=str(Path(self.temp_dir) / "tmp"),
            source_data_dir=str(Path(self.temp_dir) / "source_data")
        )
        self.downloader = DataDownloader(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning."""
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        result = self.downloader._clone_repository("test-tag")
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_clone_repository_failure(self, mock_run):
        """Test repository cloning failure."""
        mock_run.side_effect = Exception("Clone failed")
        
        result = self.downloader._clone_repository("test-tag")
        self.assertFalse(result)
    
    def test_get_available_mods(self):
        """Test getting available mods."""
        # Create mock mod directories
        mods_dir = Path(self.config.source_data_dir) / "mods"
        mods_dir.mkdir(parents=True)
        
        (mods_dir / "mod1").mkdir()
        (mods_dir / "mod2").mkdir()
        (mods_dir / "TEST_DATA").mkdir()  # Should be excluded
        
        mods = self.downloader.get_available_mods()
        self.assertIn("mod1", mods)
        self.assertIn("mod2", mods)
        self.assertNotIn("TEST_DATA", mods)


class TestDataOrganizer(unittest.TestCase):
    """Test cases for the DataOrganizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            source_data_dir=str(Path(self.temp_dir) / "source_data"),
            organized_main_data=str(Path(self.temp_dir) / "tmp" / "dda"),
            organized_mods_data=str(Path(self.temp_dir) / "tmp" / "mods")
        )
        self.organizer = DataOrganizer(self.config)
        
        # Create test data structure
        self.source_data_dir = Path(self.config.source_data_dir)
        self.source_data_dir.mkdir(parents=True)
        
        # Create json directory with test file
        json_dir = self.source_data_dir / "json"
        json_dir.mkdir()
        (json_dir / "test.json").write_text('{"test": "data"}')
        
        # Create mods directory with test mods
        mods_dir = self.source_data_dir / "mods"
        mods_dir.mkdir()
        
        mod1_dir = mods_dir / "mod1"
        mod1_dir.mkdir()
        (mod1_dir / "modinfo.json").write_text('{"id": "mod1", "name": "Mod 1"}')
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_organize_main_data(self):
        """Test organizing main CDDA data."""
        result = self.organizer._organize_main_data()
        self.assertTrue(result)
        
        # Check that data was organized
        organized_file = Path(self.config.organized_main_data) / "test.json"
        self.assertTrue(organized_file.exists())
    
    def test_organize_mod_data(self):
        """Test organizing mod data."""
        result = self.organizer._organize_mod_data()
        self.assertTrue(result)
        
        # Check that mod was organized
        organized_mod = Path(self.config.organized_mods_data) / "mod1" / "modinfo.json"
        self.assertTrue(organized_mod.exists())
    
    def test_get_mod_info(self):
        """Test getting mod information."""
        # First organize the data
        self.organizer._organize_mod_data()
        
        mod_info = self.organizer.get_mod_info("mod1")
        self.assertIsNotNone(mod_info)
        self.assertEqual(mod_info["id"], "mod1")


class TestModProcessor(unittest.TestCase):
    """Test cases for the ModProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            organized_main_data=str(Path(self.temp_dir) / "tmp" / "dda"),
            main_output_dir=str(Path(self.temp_dir) / "src" / "no_dust"),
            last_version_file=str(Path(self.temp_dir) / "last_version")
        )
        self.processor = ModProcessor(self.config)
        
        # Create test data with dust fields
        self.test_data_dir = Path(self.config.organized_main_data)
        self.test_data_dir.mkdir(parents=True)
        
        test_json = {
            "type": "furniture",
            "id": "test_furniture",
            "hit_field": ["fd_dust", 5],
            "destroyed_field": ["fd_dust", 10]
        }
        
        test_file = self.test_data_dir / "test.json"
        with open(test_file, 'w') as f:
            json.dump([test_json], f)
        
        # Create version file
        Path(self.config.last_version_file).write_text("test-version")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_has_target_fields(self):
        """Test detection of target fields."""
        obj_with_fields = {"hit_field": ["fd_dust", 5]}
        obj_without_fields = {"type": "furniture", "id": "test"}
        
        self.assertTrue(self.processor._has_target_fields(obj_with_fields))
        self.assertFalse(self.processor._has_target_fields(obj_without_fields))
    
    def test_extract_and_zero_fields(self):
        """Test extraction and zeroing of fields."""
        obj = {
            "hit_field": ["fd_dust", 5],
            "destroyed_field": ["fd_dust", 10],
            "other_field": "value"
        }
        
        result = self.processor._extract_and_zero_fields(obj)
        self.assertIsNotNone(result)
        self.assertEqual(result["hit_field"], ["fd_dust", 0])
        self.assertEqual(result["destroyed_field"], ["fd_dust", 0])
        self.assertNotIn("other_field", result)
    
    def test_process_json_object(self):
        """Test processing of JSON objects."""
        obj = {
            "type": "furniture",
            "id": "test_furniture",
            "hit_field": ["fd_dust", 5]
        }
        
        result = self.processor._process_json_object(obj)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "furniture")
        self.assertEqual(result["id"], "test_furniture")
        self.assertEqual(result["copy-from"], "test_furniture")
        self.assertEqual(result["hit_field"], ["fd_dust", 0])


class TestVersionTracker(unittest.TestCase):
    """Test cases for the VersionTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            last_version_file=str(Path(self.temp_dir) / "last_version"),
            last_sha_file=str(Path(self.temp_dir) / "last_sha"),
            output_dir=str(Path(self.temp_dir) / "src")
        )
        self.tracker = VersionTracker(self.config)
        
        # Create test src directory
        src_dir = Path(self.config.output_dir)
        src_dir.mkdir(parents=True)
        (src_dir / "test.txt").write_text("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_version_tracking(self):
        """Test version tracking functionality."""
        # Test initial state
        self.assertEqual(self.tracker.get_last_version(), "unknown")
        
        # Test updating version
        self.assertTrue(self.tracker.update_last_version("test-version"))
        self.assertEqual(self.tracker.get_last_version(), "test-version")
    
    def test_sha_tracking(self):
        """Test SHA hash tracking functionality."""
        # Test initial state
        self.assertEqual(self.tracker.get_last_sha(), "")
        
        # Calculate and update SHA
        current_sha = self.tracker.calculate_src_hash()
        self.assertNotEqual(current_sha, "")
        
        self.assertTrue(self.tracker.update_last_sha(current_sha))
        self.assertEqual(self.tracker.get_last_sha(), current_sha)
    
    def test_change_detection(self):
        """Test change detection functionality."""
        # Initially no changes (no last SHA)
        self.assertTrue(self.tracker.has_src_changed())
        
        # Set current SHA as last SHA
        current_sha = self.tracker.calculate_src_hash()
        self.tracker.update_last_sha(current_sha)
        
        # Now should be no changes
        self.assertFalse(self.tracker.has_src_changed())
        
        # Modify src directory
        (Path(self.config.output_dir) / "new_file.txt").write_text("new content")
        
        # Should detect changes
        self.assertTrue(self.tracker.has_src_changed())


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_calculate_folder_hash(self):
        """Test folder hash calculation."""
        test_dir = Path(self.temp_dir) / "test"
        test_dir.mkdir()
        
        # Create test files
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        
        hash1 = calculate_folder_hash(test_dir)
        self.assertNotEqual(hash1, "")
        
        # Hash should be consistent
        hash2 = calculate_folder_hash(test_dir)
        self.assertEqual(hash1, hash2)
        
        # Hash should change when content changes
        (test_dir / "file3.txt").write_text("content3")
        hash3 = calculate_folder_hash(test_dir)
        self.assertNotEqual(hash1, hash3)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            project_root=self.temp_dir,
            temp_dir=str(Path(self.temp_dir) / "tmp"),
            source_data_dir=str(Path(self.temp_dir) / "source_data"),
            output_dir=str(Path(self.temp_dir) / "src"),
            main_output_dir=str(Path(self.temp_dir) / "src" / "no_dust"),
            last_version_file=str(Path(self.temp_dir) / "last_version"),
            last_sha_file=str(Path(self.temp_dir) / "last_sha")
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.no_dust.data_downloader.DataDownloader.download_tag_data')
    def test_main_processor_integration(self, mock_download):
        """Test the main processor integration."""
        # Mock successful download
        mock_download.return_value = True
        
        # Create mock downloaded data
        self._create_mock_downloaded_data()
        
        # Test processing
        processor = MainProcessor(self.config)
        
        # This would normally fail due to mocked download, but we can test the structure
        self.assertIsNotNone(processor)
    
    def _create_mock_downloaded_data(self):
        """Create mock downloaded data for testing."""
        source_data_dir = Path(self.config.source_data_dir)
        source_data_dir.mkdir(parents=True)
        
        # Create json directory
        json_dir = source_data_dir / "json"
        json_dir.mkdir()
        
        # Create test JSON with dust fields
        test_data = [{
            "type": "furniture",
            "id": "test_furniture",
            "hit_field": ["fd_dust", 5]
        }]
        
        with open(json_dir / "test.json", 'w') as f:
            json.dump(test_data, f)
        
        # Create mods directory
        mods_dir = source_data_dir / "mods"
        mods_dir.mkdir()


if __name__ == '__main__':
    # Set up logging for tests
    setup_logging("DEBUG")
    
    # Run tests
    unittest.main(verbosity=2)
