from PyQt4 import QtGui
from ramps import KeyFrameList
import json


class RampEditor(QtGui.QWidget):
    """Edits ramps. Main widget of the application."""

    def __init__(self, settings):
        super(RampEditor, self).__init__()
        self.settings = settings
        self.setupUi(self)

    def setupUi(self, widget):
        self.grid = QtGui.QGridLayout(self)
        self.setLayout(self.grid)

    def openNewFile(self, path_to_new_file):
        with open(path_to_new_file, 'r') as f:
                data = json.load(f)
        self.kfl = KeyFrameList(data['keyframes'])
