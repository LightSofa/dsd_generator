"""
Copyright (c) Cutleast

Script to convert a plugin translation to a DSD file.
"""

from copy import copy
from pathlib import Path
import logging

from .plugin_interface import Plugin
from .plugin_interface.plugin_string import PluginString as String
import json

log = logging.getLogger("esp2dsd.converter")


def merge_plugin_strings(
    translation_plugin: Path, original_plugin: Path, debug: bool = False
) -> list[String]:
    """
    Extracts strings from translation and original plugin and merges them.
    """

    plugin = Plugin(translation_plugin)
    translation_strings = plugin.extract_strings()

    plugin = Plugin(original_plugin)
    original_strings = {
        f"{(string.form_id.lower() if string.form_id is not None else '')}###{string.editor_id}###{string.type}###{string.index}": string
        for string in plugin.extract_strings()
    }

    if debug:
        log.debug(
            f"Merging {len(original_strings)} original String(s) to {len(translation_strings)} translated String(s)..."
        )

    merged_strings: list[String] = []

    skipped_strings = 0

    for translation_string in translation_strings:
        original_string = original_strings.get(
            f"{(translation_string.form_id.lower() if translation_string.form_id is not None else '')}###{translation_string.editor_id}###{translation_string.type}###{translation_string.index}"
        )

        if original_string is None:
            if debug:
                log.warning(f"Not found in Original: {translation_string}")
            continue
        elif original_string.original_string == translation_string.original_string:
            skipped_strings += 1
            continue

        translation_string = copy(translation_string)
        translation_string.translated_string = translation_string.original_string
        translation_string.original_string = original_string.original_string
        translation_string.status = String.Status.TranslationComplete
        merged_strings.append(translation_string)

    if debug:
        log.warning(f"Skipped {skipped_strings} duplicate/untranslated String(s)!")
        log.debug(f"Merged {len(merged_strings)} String(s).")

    return merged_strings


def esp2dsd(
    translation_plugin: Path, original_plugin: Path, debug: bool = False
) -> str:
    """
    Converts a plugin translation to JSON string as DSD config file format.
    """

    merged_strings = merge_plugin_strings(translation_plugin, original_plugin, debug)

    string_data = [string.to_string_data() for string in merged_strings]

    return json.dumps(string_data, ensure_ascii=False, indent=4)
