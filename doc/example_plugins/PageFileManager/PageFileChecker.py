from typing import Sequence

import mobase  # type: ignore
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QMainWindow

from .PageFileManager import PageFileManager
from .Utils import check_free_space, get_pagefile_size, logger


class PageFileChecker(mobase.IPluginDiagnose):
    def __init__(self, pfm: PageFileManager) -> None:
        """
        Initializes a new instance of the PageFileChecker class.

        This constructor initializes the base class (mobase.IPluginDiagnose) and sets
        the internal PageFileManager reference to the given PageFileManager instance.

        Args:
            pfm (PageFileManager): The PageFileManager instance to set as the internal
                reference.

        Returns:
            None
        """
        # Call the constructor of the base class
        super().__init__()

        # Set the internal PageFileManager reference
        self._pfm: PageFileManager = pfm

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

        # Register the callback for the user interface initialization event
        self._organizer.onUserInterfaceInitialized(self.onUserInterfaceInitialized)

        # Log the initialization message
        logger.info("PageFileManagerChecker initialized")

        # Return True to indicate successful initialization
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

        This function returns the string "MaskedRPGFan" as the author of the plugin.

        Returns:
            str: The author of the plugin.
        """
        return "MaskedRPGFan"

    def description(self) -> str:
        """
        Returns the description of the plugin.

        This function returns the string "Checks if the pagefile is set correctly."
        as the description of the plugin.

        Returns:
            str: The description of the plugin.
        """
        return self.tr("Automatically checks if the page file is set correctly. Displays notifications.")

    def name(self) -> str:
        """
        Returns the name of the plugin.

        This function returns the string "PageFileManagerChecker" as the name of the
        plugin.

        Returns:
            str: The name of the plugin.
        """
        return "PageFile Checker"

    def version(self) -> mobase.VersionInfo:
        """
        Returns the version information of the plugin.

        This function returns a mobase.VersionInfo object with the version information
        of the plugin. The version information is set to 0.3.0-Beta.

        Returns:
            mobase.VersionInfo: The version information of the plugin.
        """
        return mobase.VersionInfo(0, 3, 0, mobase.ReleaseType.BETA)

    def onUserInterfaceInitialized(self, main_window: QMainWindow):
        """
        This function is called when the user interface is initialized.

        It checks if there are any active problems and if the "autostart"
        setting is enabled. If both conditions are met, it calls the `display()`
        function of the `PageFileManager` instance `_pfm`.

        Args:
            main_window (QMainWindow): The main window of the user interface.

        Returns:
            None
        """
        # Check if there are any active problems.
        problems: list[int] = self.activeProblems()
        if len(problems) > 0:
            # Check if the "autostart" setting is enabled.
            if self._organizer.pluginSetting(self._pfm.name(), "autostart"):
                # If page file does not exists or is too small.
                if 0 <= problems[0] <= 2:
                    # Try to fix the problem.
                    self._pfm.display()

    def settings(self) -> Sequence[mobase.PluginSetting]:
        """
        Returns a list of PluginSetting objects for the plugin settings.
        Returns:
            Sequence[mobase.PluginSetting]: The list of PluginSetting objects.
        """
        # Create a list of PluginSetting objects
        return []

    def activeProblems(self) -> list[int]:
        """
        Returns a list of problem keys indicating which problems are active.

        The list contains a single key if there is an active problem. The key
        represents the problem type.

        Returns:
            list[int]: The list of problem keys.
        """
        if not self._organizer.pluginSetting(self._pfm.name(), "enable_notifications"):
            return []

        # Get the required pagefile size from the plugin settings
        required_mb: int = self._organizer.pluginSetting(self._pfm.name(), "pagefile_size")
        maximum_mb: int = self._organizer.pluginSetting(self._pfm.name(), "pagefile_size_max")

        # Get the current pagefile size
        pagefile_size: tuple[int, int] | None = get_pagefile_size()

        # Check if there is no pagefile
        if pagefile_size is None:
            # Check if there is enough free space to create a pagefile
            if check_free_space(required_mb)[0]:
                # Return the key for the "pagefile does not exist" problem
                return [0]
            else:
                # Return the key for the "no free space for pagefile" problem
                return [2]

        # Get the maximum size of the pagefile
        initial_size_mb: int = pagefile_size[0]
        max_size_mb: int = pagefile_size[1]

        # Check if the pagefile is too small
        if initial_size_mb < required_mb or max_size_mb < maximum_mb:
            # Check if there is enough free space to increase the pagefile
            if check_free_space(required_mb - max_size_mb)[0]:
                # Return the key for the "pagefile is too small" problem
                return [1]
            else:
                # Return the key for the "no free space for pagefile" problem
                return [2]

        # Check if the pc needs to be restarted
        if self._pfm._need_restart:
            return [3]

        # Return an empty list indicating no active problems
        return []

    def fullDescription(self, key: int) -> str:
        """
        Returns a full description of the problem based on the given problem key.

        Parameters:
            key (int): The problem key.

        Returns:
            str: The full description of the problem.

        Raises:
            NotImplementedError: If the problem key is not implemented.
        """
        # Match the problem key and return the corresponding full description
        match key:
            case 0:  # Pagefile does not exist
                # Return the localized description with the required pagefile size formatted in MB
                return self.tr("The pagefile does not exist. Required size {0}-{1}MB.").format(
                    self._organizer.pluginSetting(self._pfm.name(), "pagefile_size"), self._organizer.pluginSetting(self._pfm.name(), "pagefile_size_max")
                )
            case 1:  # Pagefile is too small
                # Return the localized description with the required pagefile size and current pagefile size formatted in MB
                current_min, current_max = get_pagefile_size()
                return self.tr("The pagefile is too small. Required size {0}-{1}MB, current size {2}-{3}MB.").format(
                    self._organizer.pluginSetting(self._pfm.name(), "pagefile_size"),
                    self._organizer.pluginSetting(self._pfm.name(), "pagefile_size_max"),
                    current_min,
                    current_max,
                )
            case 2:  # No free space is available
                return self.tr("No free space is available to create the pagefile.")
            case 3:  # PC needs to be restarted
                return self.tr("The PC needs to be restarted to create the pagefile.")
            case _:  # Unimplemented problem key
                raise NotImplementedError

    def hasGuidedFix(self, key: int) -> bool:
        """
        Returns whether the given problem key has a guided fix.

        Parameters:
            key (int): The problem key.

        Returns:
            bool: True if the problem key has a guided fix, False otherwise.

        Raises:
            NotImplementedError: If the problem key is not implemented.
        """
        # Match the problem key and return True if there is a guided fix
        match key:
            case 0:  # Pagefile does not exist
                return True
            case 1:  # Pagefile is too small
                return True
            case 2:  # No free space is available
                return False
            case 3:  # PC needs to be restarted
                return True
            case _:  # Unimplemented problem key
                # Raise a NotImplementedError if the problem key is not implemented
                raise NotImplementedError

    def shortDescription(self, key: int) -> str:
        """
        Returns a short description of the problem based on the given problem key.

        Parameters:
            key (int): The problem key.

        Returns:
            str: The short description of the problem.

        Raises:
            NotImplementedError: If the problem key is not implemented.
        """
        # Match the problem key and return the corresponding short description
        match key:
            case 0:  # Pagefile does not exist
                return self.tr("The pagefile does not exist.")
            case 1:  # Pagefile is too small
                return self.tr("The pagefile is too small.")
            case 2:
                return self.tr("No free space for pagefile.")
            case 3:  # PC needs to be restarted
                return self.tr("Need to restart the PC.")
            case _:  # Unimplemented problem key
                # Raise a NotImplementedError if the problem key is not implemented
                raise NotImplementedError

    def startGuidedFix(self, key: int) -> None:
        """
        This function is called when a user wants to apply a guided fix for a specific problem.

        This function is responsible for starting the guided fix process for a specific problem.
        It takes a problem key as input and based on the key, it calls the appropriate function
        to perform the guided fix.

        Parameters:
            key (int): The problem key.

        Raises:
            NotImplementedError: If the problem key is not implemented.
        """
        # Match the problem key and call the corresponding function
        match key:
            case 0:  # Pagefile does not exist
                # Call the display function to create the pagefile
                self._pfm.display()
            case 1:  # Pagefile is too small
                # Call the display function to increase the pagefile size
                self._pfm.display()
            case 3:  # PC needs to be restarted
                self._pfm.ask_for_restart()
            case _:  # Unimplemented problem key
                # Raise a NotImplementedError if the problem key is not implemented
                raise NotImplementedError

    def master(self) -> str:
        """
        Returns the name of the master plugin that this plugin is associated with.

        Returns:
            str: The name of the master plugin.
        """
        # Return the name of the master plugin
        return self._pfm.name()
