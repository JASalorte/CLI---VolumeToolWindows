# CLI---WindowsVolumeTool

[![Tests](https://github.com/JASalorte/CLI---VolumeToolWindows/actions/workflows/tests.yml/badge.svg)](https://github.com/JASalorte/CLI---VolumeToolWindows/actions/workflows/tests.yml)
[![Lint](https://github.com/JASalorte/CLI---VolumeToolWindows/actions/workflows/lint.yml/badge.svg)](https://github.com/JASalorte/CLI---VolumeToolWindows/actions/workflows/lint.yml)
[![Coverage Status](https://coveralls.io/repos/github/JASalorte/CLI---VolumeToolWindows/badge.svg?branch=main)](https://coveralls.io/github/JASalorte/CLI---VolumeToolWindows?branch=main)

Audio Tool for Windows

A simple Python utility to list, inspect, and control the volume and mute status of applications and system sounds on Windows via the Windows Core Audio APIs.

## Features

- List active audio sessions with process names and current volume levels
- Set the volume for specific applications (case-insensitive matching)
- Adjust or mute "System Sounds" separately from app sessions
- Provides a clean CLI interface and is covered with a robust pytest suite for quality assurance

## Usage

```bash
# List active audio sessions
python -m audio_tool list

# Interactively select one and set volume
python -m audio_tool select

# Set volume directly by name
python -m audio_tool set "Discord.exe" 50
python -m audio_tool set "Discord.exe" 0.5

# Toggle mute
python -m audio_tool toggle "Discord.exe"
```

## Quick Install

```bash
git clone https://github.com/JASalorte/CLI---VolumeToolWindows.git
cd CLI---WindowsVolumeTool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m audio_tool list
```

## Tests

This project includes a comprehensive pytest suite (78 tests total) covering:
- CLI command behavior
- Core volume manipulation logic
- Utility functions

Tests run automatically via GitHub Actions on Windows with Python versions from 3.8 to 3.12.

[View Test Report](https://jasalorte.github.io/CLI---VolumeToolWindows/reports/report.html?sort=result)
(It updates automatically on every push)

To run the full suite:
```bash
cd ../CLI---WindowsVolumeTool
python -m pytest -v
```

See them in the [tests](tests/) directory.

This project is designed as both a practical tool and a learning resource for software testing (mocking, parametrized tests, and QA practices).
