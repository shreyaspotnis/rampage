from PyQt4 import QtGui


class RampEditor(QtGui.QWidget):
    """Edits ramps. Main widget of the application."""

    def __init__(self, settings):
        super(RampEditor, self).__init__()
        self.settings = settings
        self.setupUi(self)

    def setupUi(self, widget):
        pass

    def openNewFile(self, path_to_new_file):
        print(path_to_new_file)
