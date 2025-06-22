import mobase
from .esp2dsd_batch_converter import DSDGenerator

def createPlugin() -> mobase.IPlugin:
    return DSDGenerator()
