from PyQt4 import QtGui, QtCore
import json

from KeyFrameWidgets import QKeyFrameList
from ChannelWidgets import QChannel
from ChannelWidgets import QEditChannelInfoDialog
from RampViewer import RampViewer
from DictEditor import DictEditor
from rampage import ramps


def clearLayout(layout):
    """Removes all widgets in the layout. Useful when opening a new file, want
    to clear everything."""
    while layout.count():
        child = layout.takeAt(0)
        child.widget().deleteLater()


class RampEditor(QtGui.QWidget):

    """Edits ramps. Main widget of the application."""

    ramp_changed = QtCore.pyqtSignal()
    time_changed = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(RampEditor, self).__init__()
        self.settings = settings
        self.setupUi(self)

    def setupUi(self, widget):
        self.grid = QtGui.QGridLayout(self)
        self.grid.setSpacing(0)
        self.setLayout(self.grid)
        self.time_changed.connect(self.handleTimeChanged)
        self.scroll_area = None

    def handleProperties(self):
        if 'properties' not in self.data:
            self.data['properties'] = {}
        d_new = dict(self.data['properties'])
        dialog = DictEditor(d_new, 'Properties', self)
        if dialog.exec_():
            self.data['properties'] = d_new
            self.ramp_changed.emit()

    def setScrollWidget(self, scroll_area):
        self.scroll_area = scroll_area

    def openNewFile(self, path_to_new_file):
        with open(path_to_new_file, 'r') as f:
            data = json.load(f)
        self.data = data
        self.reDoUi()

    def handleTimeChanged(self):
        print('Time changed')

    def reDoUi(self, set_focus_on=None):
        self.ramp_changed.emit()
        clearLayout(self.grid)
        self.kfl = QKeyFrameList(self.data['keyframes'], self.settings,
                                 self.grid,
                                 start_pos=(0, 1), parent_widget=self,
                                 set_focus_on=set_focus_on)
        # TODO: make channels sorted here
        self.channels = []
        sorted_repr = sorted(self.data['channels'].items(),
                             key=lambda x: x[1]['id'])
        sorted_keys = [sr[0] for sr in sorted_repr]
        for i, ch_name in enumerate(sorted_keys):
            ch_dct = self.data['channels'][ch_name]
            if ch_dct['type'] == 'analog':
                ch = QChannel(ch_name, ch_dct, self.kfl,
                              self.settings, self.grid, self,
                              ramps.analog_ramp_types, start_pos=(i+2, 0))
            elif ch_dct['type'] == 'digital':
                ch = QChannel(ch_name, ch_dct, self.kfl,
                              self.settings, self.grid, self,
                              ramps.digital_ramp_types, start_pos=(i+2, 0))
            self.channels.append(ch)

        self.properties_button = QtGui.QPushButton('Properties')
        self.properties_button.clicked.connect(self.handleProperties)
        self.grid.addWidget(self.properties_button, 0, 0)

    def handleEditChannelInfo(self, ch_name):

        out_tuple = QEditChannelInfoDialog(ch_name,
                                           self.data['channels'][ch_name],
                                           self).exec_()
        exec_return, new_key_name, new_comment, new_id = out_tuple
        if exec_return == QtGui.QDialog.Accepted:
            old_id = self.data['channels'][ch_name]['id']
            self.data['channels'][ch_name]['comment'] = new_comment
            self.data['channels'][ch_name]['id'] = new_id
            old_channel = self.data['channels'].pop(ch_name)
            self.data['channels'][new_key_name] = old_channel

            # find the channel which was changed
            for ch in self.channels:
                if ch.ch_name == ch_name:
                    ch.edit_channel_info(new_key_name,
                                         self.data['channels'][new_key_name])
            # re do the whole UI if the channel id has changed
            if old_id != new_id:
                self.reDoUi()
            else:
                self.ramp_changed.emit()
            print('Accepted')

    def handleViewChannel(self, ch_name):
        RampViewer(self.data, ch_name, self.settings, self).exec_()

    def save(self, path_to_file):
        json_file_as_string = json.dumps(self.data, indent=4,
                                         separators=(',', ': '))
        with open(path_to_file, 'w') as f:
            f.write(json_file_as_string)

    def getTimeCellRectangles(self):
        n_cols = self.grid.columnCount()
        labels = self.kfl.sorted_key_list()
        return [self.grid.cellRect(0, i) for i in range(1, n_cols)], labels

    def getChannelCellRectangles(self):
        n_rows = self.grid.columnCount()
        labels = [ch.ch_name for ch in self.channels]
        return [self.grid.cellRect(i, 0) for i in range(2, n_rows)], labels
