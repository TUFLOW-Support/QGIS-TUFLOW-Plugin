try: # Running in QGIS
    if __name__ != 'tuflow.swangis.swangis':  # not being called from tuflow plugin
        from swangis.ui import PluginMenuUI

    def name():
        return "SWAN"


    def description():
        return "Tools for building SWAN models"


    def version():
        return "0.0.1"


    def icon():
        return ""


    def qgisMinimumVersion():
        return "3.6"


    def author():
        return "Jonah Chorley"


    def email():
        return ""


    def classFactory(iface):
        """Entry point for QGIS"""
        if __name__ != 'tuflow.swangis.swangis':  # not being called from tuflow plugin
            return PluginMenuUI(iface)

except ModuleNotFoundError:
    # Running outside QGIS
    from swan import *
    from plotting import *
    # from downloads import *
