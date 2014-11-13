from PyQt4 import QtGui, QtCore
from widgets.KeyFrameWidgets import QKeyFrameList
from widgets.ChannelWidgets import QChannel, QEditChannelInfoDialog
import json
import operator


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
        sorted_repr = sorted(self.data['channels'].items(),
                             key=lambda x: x[1]['id'])
        sorted_keys = [sr[0] for sr in sorted_repr]
        for i, ch_name in enumerate(sorted_keys):
            ch_dct = self.data['channels'][ch_name]
            if ch_dct['type'] == 'analog':
                ch = QChannel(ch_name, ch_dct, self.kfl,
                              self.settings, self.grid, self,
                              start_pos=(i+2, 0))
            self.channels.append(ch)

    def handleEditChannelInfo(self, ch_name):
        print(ch_name)

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

    def save(self, path_to_file):
        json_file_as_string = json.dumps(self.data, indent=4,
                                         separators=(',', ': '))
        with open(path_to_file, 'w') as f:
            f.write(json_file_as_string)
