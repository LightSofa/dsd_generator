import os
import subprocess
from typing import Sequence

import mobase  # type: ignore
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

from .Utils import check_free_space, get_pagefile_size, logger, set_pagefile_size


class PageFileManager(mobase.IPluginTool):
    def __init__(self) -> None:
        """
        Initializes a new instance of the PageFileManager class.

        This constructor initializes the base class (mobase.IPluginTool) and sets
        the internal organizer reference to None.

        Parameters:
            None

        Returns:
            None
        """
        # Call the constructor of the base class
        super().__init__()

        # Initialize the internal organizer reference to None
        self._organizer: mobase.IOrganizer = None
        " Internal organizer reference. "

        self._need_restart: bool = False
        " Flag indicating if a PC restart is needed. "

    def init(self, organizer: mobase.IOrganizer) -> bool:
        """
        Initializes the plugin with the given organizer.

        This function is called by the organizer to initialize the plugin.
        It sets the internal organizer reference and returns True to indicate
        successful initialization.

        Args:
            organizer (mobase.IOrganizer): The organizer object.

        Returns:
            bool: True if the initialization was successful, False otherwise.
        """
        # Set the internal organizer reference
        self._organizer: mobase.IOrganizer = organizer
        self.validate_settings()
        logger.info("PageFile Manager initialized")
        return True

    def tr(self, txt: str) -> str:
        """
        Translates the given text using the QCoreApplication.translate function.

        This function uses the QCoreApplication.translate function to translate the given text
        using the context "PageFileManager". The translated text is then returned.

        Args:
            txt (str): The text to be translated.

        Returns:
            str: The translated text.
        """
        # Translate the given text using the context "PageFileManager"
        # and return the translated text
        return QCoreApplication.translate("PageFileManager", txt)

    def author(self) -> str:
        """
        Returns the author of the plugin.

        This function returns a string that contains the name of the author of the plugin.

        Returns:
            str: The name of the author of the plugin.
        """
        # The author of the plugin.
        return "MaskedRPGFan"

    def description(self) -> str:
        """
        Returns the description of the plugin.

        This function returns a string that describes what the plugin does.
        It is used to provide information about the plugin in the user interface.

        Returns:
            str: The description of the plugin.
        """
        # Return the localized description of the plugin as a string.
        return self.tr("Sets the pagefile to the desired size, and if it does not exist, creates it.")

    def name(self) -> str:
        """
        Returns the name of the plugin.

        This function returns the name of the plugin as a string.
        It is used to identify the plugin in the user interface.

        Returns:
            str: The name of the plugin.
        """
        # The name of the plugin
        # It is used to identify the plugin in the user interface
        return "PageFile Manager"

    def localizedName(self) -> str:
        """
        Returns the localized name of the plugin.

        This function returns the localized name of the plugin as a string.
        It is used to display the plugin name in the user interface.

        Returns:
            str: The localized name of the plugin.
        """
        # Return the localized name of the plugin as a string.
        return self.tr("PageFile Manager")

    def requirements(self) -> list[mobase.IPluginRequirement]:
        """
        Returns an empty list of plugin requirements.

        This function is part of the IPluginTool interface and is used to specify
        the dependencies of the plugin. In this case, the plugin does not have
        any specific dependencies, so we return an empty list.

        Returns:
            list[mobase.IPluginRequirement]: An empty list of plugin requirements.
        """
        # This plugin does not have any specific requirements, so we return an empty list.
        return []

    def settings(self) -> Sequence[mobase.PluginSetting]:
        """
        Returns a list of PluginSetting objects for the plugin settings.

        The list contains four PluginSetting objects with the following settings:

        1. name: "pagefile_size"
           description: "Minimal size of your pagefile in MB."
           default_value: 20 * 1024 (20 MB)

        2. name: "pagefile_size_max"
           description: "Maximal size of your pagefile in MB."
           default_value: 40 * 1024 (40 MB)

        3. name: "enable_notifications"
          description: "Enable notifications displayed in notification window when you use Notification button."
          default_value: True

        4. name: "autostart"
          description: "Enable automatic page file setting at startup."
          default_value: True

        5. name: "dark-theme"
          description: "Enable dark theme icon."
          default_value: True
        """
        return [
            mobase.PluginSetting("pagefile_size", self.tr("Minimal size of your pagefile in MB."), 20 * 1024),
            mobase.PluginSetting("pagefile_size_max", self.tr("Maximal size of your pagefile in MB."), 40 * 1024),
            mobase.PluginSetting("enable_notifications", self.tr("Enable notifications displayed in Notifications window when you use Notifications button."), True),
            mobase.PluginSetting("autostart", self.tr("Enable automatic page file setting at startup."), True),
            mobase.PluginSetting("dark-theme", self.tr("Enable dark theme icon."), False),
        ]

    def version(self) -> mobase.VersionInfo:
        """
        Returns the version information of the plugin.

        This function returns a mobase.VersionInfo object with the version information
        of the plugin. The version information is set to 0.3.0-Beta.

        Returns:
            mobase.VersionInfo: The version information of the plugin.
        """
        return mobase.VersionInfo(0, 3, 0, mobase.ReleaseType.BETA)

    def display(self) -> None:
        """
        Displays information about the pagefile and sets it to the desired size if necessary.
        """

        self.validate_settings()
        # Retrieve the required pagefile size from settings
        required_mb: int = self._organizer.pluginSetting(self.name(), "pagefile_size")
        maximum_mb: int = self._organizer.pluginSetting(self.name(), "pagefile_size_max")

        # Get the current pagefile size and drive letter
        pagefile_size: tuple[int, int] | None = get_pagefile_size()
        drive_letter: str = os.path.splitdrive(os.path.abspath(__file__))[0]

        if pagefile_size:
            # Pagefile exists, check if it needs to be resized
            initial_size_mb: int = pagefile_size[0]
            max_size_mb: int = pagefile_size[1]

            # Log the pagefile information
            logger.info(self.tr("Pagefile found on drive {0}: {1}-{2} MB.").format(drive_letter, initial_size_mb, max_size_mb))

            if initial_size_mb < required_mb or max_size_mb < maximum_mb:
                # Pagefile is too small, check if enough free space is available
                result: tuple[bool, float] = check_free_space(required_mb - max_size_mb)
                success: bool = result[0]
                free_mb: float = result[1]

                if success:
                    # Enough free space available, resize the pagefile
                    result: QMessageBox.StandardButton = QMessageBox.question(
                        self._parentWidget(),
                        self.tr("Pagefile is too small."),
                        self.tr(
                            "Page file on drive {0} is too small. {1}-{2}MB required, but only {3}-{4}MB available. Do you want to automatically set it to {1}-{2}MB?"
                        ).format(drive_letter, required_mb, maximum_mb, initial_size_mb, max_size_mb),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if result == QMessageBox.StandardButton.Yes:
                        set_pagefile_size(required_mb, maximum_mb)
                        self.ask_for_restart()
                        self._need_restart = True
                else:
                    # Not enough free space available, display an error message
                    QMessageBox.critical(
                        self._parentWidget(),
                        self.tr("Need more free space."),
                        self.tr("Not enough disk space available. {0}MB required, but only {1:.2f}MB available.").format(required_mb, free_mb),
                    )
                    return
            else:
                # Pagefile is already large enough, display a success message
                QMessageBox.information(self._parentWidget(), self.tr("Pagefile is correct."), self.tr("Page file has correct size. No need to change anything."))
                return
        else:
            # Pagefile does not exist, check if enough free space is available
            if check_free_space(required_mb)[0]:
                # Enough free space available, create and set the pagefile
                result: QMessageBox.StandardButton = QMessageBox.question(
                    self._parentWidget(),
                    self.tr("Pagefile does not exists."),
                    self.tr("Pagefile not found on drive {0}. Do you want to automatically create and set it to {1}-{2}MB?").format(drive_letter, required_mb, maximum_mb),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if result == QMessageBox.StandardButton.Yes:
                    logger.info(self.tr("Pagefile not found on drive {0}. Automatically creating and setting to {1}-{2}MB.").format(drive_letter, required_mb, maximum_mb))
                    set_pagefile_size(required_mb, maximum_mb)
                    self.ask_for_restart()
                    self._need_restart = True
            else:
                QMessageBox.warning(
                    self._parentWidget(),
                    self.tr("Need more free space."),
                    self.tr("Pagefile not found on drive {0}. Not enough space to create the pagefile.").format(drive_letter),
                )
                logger.info(f"Pagefile not found on drive {drive_letter}. Not enough space to create the pagefile.")
                return

    def displayName(self) -> str:
        """
        Returns the name of the plugin's display.

        This function returns the name of the plugin's display as a string.
        It is used to display the plugin's name in the Organizer.

        Returns:
            str: The name of the plugin's display.
        """
        # Returns the name of the plugin's display as a string
        return self.tr("PageFile Manager")

    def icon(self) -> QIcon:
        """
        Returns the icon for the plugin.

        This function returns a QIcon object that represents the icon for the plugin.
        This function is part of the IPluginTool interface and is used to get the icon
        for the plugin.

        Returns:
            QIcon: The QIcon object representing the icon for the plugin.
        """
        # The icon for the plugin.
        # This function returns a QIcon object that represents the icon for the plugin.
        # The plugin icon is used to display the plugin in the Organizer.

        # Load the icon file from the main MO2 directory
        if self._organizer.pluginSetting(self.name(), "dark-theme"):
            return QIcon("plugins/PageFileManager/PageFileManager-Dark.svg")
        else:
            return QIcon("plugins/PageFileManager/PageFileManager.svg")

    def tooltip(self) -> str:
        """
        Returns the tooltip text for the plugin.

        This function returns a string that contains the tooltip text for the plugin.
        The tooltip text is used to provide information about what the plugin does.

        Returns:
            str: The tooltip text for the plugin.
        """
        # The tooltip text for the plugin.
        # The tooltip text is used to provide information about what the plugin does.
        return self.tr("Set pagefile according to settings.")

    def ask_for_restart(self) -> None:
        """
        Prompts the user to confirm a system restart after setting the pagefile.

        Displays a message box with 'Confirm Restart' and 'Pagefile was set properly. Do you want to restart the computer?'.
        The user can choose between 'Yes' and 'No'. If 'Yes' is selected, the system will attempt to restart immediately.
        If 'No' is selected, a message box will be displayed asking the user to restart the system manually later.

        Parameters:
            None

        Returns:
            None
        """
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self._parentWidget(),
            self.tr("Confirm Restart"),
            self.tr("Pagefile was set properly. Do you want to restart the computer?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self._parentWidget(), self.tr("Error"), self.tr("Failed to restart the computer: {0}").format(e))
        else:
            QMessageBox.information(self._parentWidget(), self.tr("Restart required!"), self.tr("Please restart the system manually later to apply the changes."))

    def validate_settings(self) -> None:
        """
        Validates the plugin settings and adjusts them if necessary.

        This function ensures that the plugin settings are valid and consistent.
        If the minimum size is negative, it is set to 20GB.
        If the minimum size is larger than the maximum size, the maximum size is
        set to the minimum size.

        Parameters:
            None

        Returns:
            None
        """
        # Get the minimum and maximum pagefile sizes from the plugin settings
        min_size: int = self._organizer.pluginSetting(self.name(), "pagefile_size")
        max_size: int = self._organizer.pluginSetting(self.name(), "pagefile_size_max")

        # Set the minimum size to 20GB if it is negative
        if min_size < 0:
            min_size = 20 * 1024
            logger.warning("Settings fix. Minimum pagefile below zero. Minimum pagefile size set to 20GB.")
            self._organizer.setPluginSetting(self.name(), "pagefile_size", min_size)

        # Set the maximum size to the minimum size if it is smaller
        if min_size > max_size:
            self._organizer.setPluginSetting(self.name(), "pagefile_size_max", min_size)
            logger.warning("Settings fix. Maximum pagefile size below minimum. Maximum pagefile size set to minimum pagefile size.")
