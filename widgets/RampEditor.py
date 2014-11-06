from PyQt4 import QtGui, QtCore
from widgets.KeyFrameWidgets import QKeyFrameList
from widgets.ChannelWidgets import QChannel
import json


def clearLayout(layout):
    """Removes all widgets in the layout. Useful when opening a new file, want
    to clear everything."""
    while layout.count():
        child = layout.takeAt(0)
        child.widget().deleteLater()


class RampEditor(QtGui.QWidget):

    """Edits ramps. Main widget of the application."""

    ramp_changed = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(RampEditor, self).__init__()
        self.settings = settings
        self.setupUi(self)

    def setupUi(self, widget):
        self.grid = QtGui.QGridLayout(self)
        self.grid.setSpacing(0)
        self.setLayout(self.grid)

    def openNewFile(self, path_to_new_file):
        with open(path_to_new_file, 'r') as f:
                data = json.load(f)
        self.data = data
        self.reDoUi()

    def reDoUi(self, set_focus_on=None):
        self.ramp_changed.emit()
        clearLayout(self.grid)
        self.kfl = QKeyFrameList(self.data['keyframes'], self.settings,
                                 self.grid,
                                 start_pos=(0, 1), parent_widget=self,
                                 set_focus_on=set_focus_on)
        # TODO: make channels sorted here
        self.channels = []
        for i, ch_name in enumerate(self.data['channels']):
            ch = QChannel(ch_name, self.data['channels'][ch_name], self.kfl,
                          self.settings, self.grid, self,
                          start_pos=(i+2, 0))
            self.channels.append(ch)

    def save(self, path_to_file):
        json_file_as_string = json.dumps(self.data, indent=4,
                                         separators=(',', ': '))
        with open(path_to_file, 'w') as f:
            f.write(json_file_as_string)
