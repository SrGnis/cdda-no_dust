# CDDA No Dust Mod Automation

An automated system for creating no-dust mods for Cataclysm: Dark Days Ahead (CDDA) from the official repository data.

## Overview

This automation system downloads data from the CDDA repository, processes it to remove dust generation effects, and creates separate mod packages for the main game and individual mods. The system can run continuously to automatically process new CDDA releases.

## Features

- **Automated Processing**: Automatically checks for new CDDA tags and processes them
- **Modular Design**: Separate mods for main game and individual mod content
- **Version Tracking**: Tracks processed versions and detects changes
- **Git Integration**: Automatically commits, tags, and pushes changes
- **Error Handling**: Comprehensive error handling with recovery mechanisms
- **CI/CD Ready**: GitHub Actions workflows for automated operation
- **Testing**: Complete test suite for all components

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Git
- Access to the CDDA repository (public)

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd cdda-no_dust
```

2. Install dependencies (if any):
```bash
pip install -r requirements.txt  # If you have additional dependencies
```

3. Configure the system:
```bash
# The default config.json should work out of the box
# Modify config.json if you need custom settings
```

### Manual Processing

Process a specific CDDA tag:
```bash
python -m src.no_dust.main_processor cdda-experimental-2025-07-04-0449
```

### Pipeline Processing

Run the pipeline once:
```bash
python -m src.no_dust.pipeline_automation --single-run
```

Run continuous processing (checks every hour):
```bash
python -m src.no_dust.pipeline_automation --check-interval 3600
```

## Architecture

### Core Components

1. **Main Processor** (`main_processor.py`): Orchestrates the complete processing pipeline
2. **Data Downloader** (`data_downloader.py`): Downloads data from CDDA repository using sparse checkout
3. **Data Organizer** (`data_organizer.py`): Organizes downloaded data into proper structure
4. **Mod Processor** (`mod_processor.py`): Processes JSON files to create no-dust mods
5. **Pipeline Automation** (`pipeline_automation.py`): Handles continuous automation
6. **Version Tracker** (`version_tracker.py`): Tracks versions and changes
7. **Git Manager** (`git_manager.py`): Handles git operations

### Data Flow

```
CDDA Repository → Download → Organize → Process → Output Mods → Git Operations
```

1. **Download**: Sparse checkout of `data/json` and `data/mods` from CDDA repository
2. **Organize**: Move `data/json` to `tmp/dda/` and individual mods to `tmp/mods/`
3. **Process**: Create no-dust versions by zeroing `hit_field` and `destroyed_field` values
4. **Output**: Generate `src/no_dust/` and `src/no_dust_<modname>/` folders
5. **Git**: Commit, tag, and push changes

### Output Structure

```
src/
├── no_dust/                    # Main CDDA no-dust mod
│   ├── modinfo.json
│   └── [processed JSON files]
├── no_dust_aftershock/         # Aftershock no-dust mod
│   ├── modinfo.json
│   └── [processed JSON files]
├── no_dust_magiclysm/          # Magiclysm no-dust mod
│   ├── modinfo.json
│   └── [processed JSON files]
└── ...                         # Other mod-specific folders
```

## Configuration

The system is configured via `config.json`. Key settings:

```json
{
  "source_repo_url": "https://github.com/CleverRaven/Cataclysm-DDA.git",
  "output_dir": "src",
  "main_output_dir": "src/no_dust",
  "mod_output_prefix": "src/no_dust_",
  "excluded_mods": ["dda", "TEST_DATA", "default.json"],
  "mod_template": {
    "type": "MOD_INFO",
    "id": "no_dust_{mod_name}",
    "name": "No Dust - {mod_display_name}",
    "dependencies": ["dda", "{mod_name}"]
  }
}
```

## GitHub Actions

### Automated Workflow

The system includes GitHub Actions workflows:

- **automation.yml**: Runs every 6 hours to check for new CDDA releases
- **manual-test.yml**: Manual workflow for testing specific tags

### Setup for GitHub Actions

1. Ensure the repository has write permissions for GitHub Actions
2. The workflows will automatically:
   - Check for new CDDA tags
   - Process new releases
   - Commit and push changes
   - Create release tags
   - Handle errors and notifications

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run specific test categories:
```bash
# Unit tests only
python -m pytest tests/test_automation.py::TestConfig -v

# Integration tests
python -m pytest tests/test_automation.py::TestIntegration -v
```

## Monitoring and Debugging

### Log Files

- `automation.log`: Main automation log
- `error_log.json`: Structured error log with recovery information

### Status Checking

Check the current status:
```bash
python -c "
from src.automation.version_tracker import VersionTracker
from src.automation.config import Config
config = Config.load_from_file('config.json')
tracker = VersionTracker(config)
status = tracker.get_tracking_status()
print('Status:', status)
"
```

### Manual Recovery

Reset tracking (useful for testing):
```bash
python -c "
from src.automation.version_tracker import VersionTracker
from src.automation.config import Config
config = Config.load_from_file('config.json')
tracker = VersionTracker(config)
tracker.reset_tracking()
print('Tracking reset')
"
```

## Troubleshooting

### Common Issues

1. **Download Failures**: Check internet connection and CDDA repository availability
2. **Processing Errors**: Verify JSON file formats and processing logic
3. **Git Errors**: Check repository permissions and git configuration
4. **Configuration Errors**: Validate config.json format and required fields

### Error Recovery

The system includes automatic error recovery:
- Download failures: Cleanup partial downloads and retry
- Processing errors: Restore from backup if available
- Git errors: Reset to clean state when possible

### Manual Intervention

If automation fails:
1. Check error logs
2. Run manual processing for specific tags
3. Use backup restoration if needed
4. Reset tracking files if necessary

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the error logs
2. Review the troubleshooting section
3. Create an issue in the repository
4. Include relevant log files and configuration
