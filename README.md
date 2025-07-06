# CDDA No Dust Mod

A mod collection that prevents the generation of dust in CDDA.

## Overview

This automation system downloads data from the CDDA repository, processes it to remove dust generation effects, and creates separate mod packages for the main game and individual mods.

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
git clone https://github.com/SrGnis/cdda-no_dust
cd cdda-no_dust
```

2. Install dependencies (if any):
```bash
pip install -r requirements.txt
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

Run the pipeline:
```bash
python -m src.no_dust.pipeline_automation
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
src/dist/
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
