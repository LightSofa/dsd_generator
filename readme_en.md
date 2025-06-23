# DSD Generator

DSD Generator is a Mod Organizer 2 plugin that automatically generates DSD configuration files from translation patches. It scans all enabled mods and processes translation patches in batch.

## Features

- Automatically scan all enabled mods for translation patches (`.esp`, `.esm`, `.esl`)
- Generate DSD configuration files using the built-in ESP2DSD Python tool
- Save configurations to a new mod directory (named by date/time or custom name)
- Blacklist support to exclude specific plugins, folders, or mod IDs
- Optionally copy generated configs to original translation patch directories
- Automatically hide original translation ESP files (by adding `.mohidden` suffix)
- Supports auto-run when launching the game
- Remembers incorrect translation pairs to avoid repeated processing

## Installation

1. Place the `esp2dsd_batch_converter` folder into the `plugins` directory of Mod Organizer 2.
2. Restart Mod Organizer 2.

## Usage

1. Find `Generate DSD Configs` in the `Tools` menu of Mod Organizer 2.
2. In the settings dialog:
   - Choose whether to copy configs to translation patch directories.
   - [Optionally] set a custom output mod name.
   - [Optionally] Add plugin names, folders, or mod IDs to the blacklist (one per line).
3. After clicking OK, the plugin will:
   1. Scan all enabled mods.
   2. Identify translation patches.
   3. Generate DSD configuration files.
   4. Create a new mod with the generated files.


## Advanced Features

- **Blacklist**: Add plugin names, mod folders, or mod IDs to exclude from processing (one per line).
  - Blacklist Syntax:
    - Plugin name: `SomePatch.esp`
    - Mod folder: `SomeMod/`
    - Mod folder by modID: `@123456` (from `meta.ini`)
    - Lines starting with `#` are comments.
  
- **Auto-replace**: Automatically copy generated configs to translation patch directories and hide original ESPs.
- **Auto Run**:  generate DSD configs automatically when launching the game. This feature can be enabled in the MO2 plugin settings panel.
- **Error Handling**: Incorrect translation plugins are recorded and skipped in future runs.

## Notes

- Generated files are saved in a new mod named "DSD_Configs_YY-MM-DD-HH-MM" or your custom name.
- When using auto-replace, original ESP files are renamed with ".mohidden" suffix.

 
## License

MIT