from typing import List

import mobase  # type: ignore

from .page_file_checker import PageFileChecker
from .page_file_manager import PageFileManager
from .utils import create_logger


def createPlugins() -> List[mobase.IPlugin]:
    """
    Creates and returns a list of mobase plugins.

    :return: A list of mobase plugins.
    :rtype: List[mobase.IPlugin]
    """
    # Create a logger instance
    create_logger()

    # Create an instance of the PageFileManager
    pfm: PageFileManager = PageFileManager()

    # Create an instance of the PageFileChecker and pass the PageFileManager instance to it
    page_file_checker: PageFileChecker = PageFileChecker(pfm)

    # Return a list containing the PageFileManager and PageFileChecker instances
    return [pfm, page_file_checker]
