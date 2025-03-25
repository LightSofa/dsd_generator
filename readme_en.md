# DSD Generator

DSD Generator is a Mod Organizer 2 plugin that automatically generates DSD configuration files from translation patches. It scans all enabled mods and processes translation patches in batch.

## Features

- Automatically scan all enabled mods for translation patches
- Generate DSD configuration files using ESP2DSD tool
- Save configurations to a new mod directory
- Blacklist support to exclude specific plugins
- Optional copying of generated configs to original translation patch directories
- Automatic hiding of original translation ESP files (by adding .mohidden suffix)

## Installation

1. Place the `esp2dsd_batch_converter` folder into the `plugins` directory of Mod Organizer 2
2. Download [esp2dsd](https://www.nexusmods.com/skyrimspecialedition/mods/107676?tab=files)
3. Restart Mod Organizer 2

## Usage

1. Find `Generate DSD Configs` in the `Tools` menu of Mod Organizer 2
2. In the settings dialog:
   - Set the path to esp2dsd.exe
   - Choose whether to copy configs to translation patch directories
   - Add plugin names to the blacklist if needed
3. After clicking OK, the plugin will:
   - Scan all enabled mods
   - Identify translation patches
   - Generate DSD configuration files
   - Create a new mod with the generated files

## Advanced Features

- **Blacklist**: Add plugin names to exclude from processing (one per line)
- **Auto-Copy Option**: Automatically copy generated configs to translation patch directories and hide original ESPs
- **Conflict Resolution**: Automatically selects the highest priority version when multiple translation patches exist

## Notes

- Generated files are saved in a new mod named "DSD_Configs_YY-MM-DD-HH-MM"
- When using auto-copy, original ESP files are renamed with ".mohidden" suffix
- Ensure ESP2DSD tool is properly installed and configured

## License
MIT