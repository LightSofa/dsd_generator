import mobase
from .dsd_generator import DSDGenerator

def createPlugin() -> mobase.IPlugin:
    return DSDGenerator()
