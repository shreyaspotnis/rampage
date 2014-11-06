from PyQt4 import QtGui, QtCore
from ramps import Channel, ramp_types
from widgets.CommonWidgets import QMultipleSpinBoxEdit
import format as fmt


class QChannelInfoBox(QtGui.QWidget):

    """Displays channel name, comment and other info."""

    def __init__(self, ch_name, dct, parent):
        super(QChannelInfoBox, self).__init__(parent)
        self.ch_name = ch_name
        self.dct = dct

        self.vbox = QtGui.QVBoxLayout(self)
        self.setLayout(self.vbox)

        self.ch_name_label = QtGui.QLabel(self)
        self.vbox.addWidget(self.ch_name_label)
        self.ch_name_label.setText(fmt.b(fmt.green(ch_name)))
        self.generateToolTip()

        # create actions to edit the keyframe
        self.edit_action = QtGui.QAction('&Edit', self)

        # connect actions to slots
        self.edit_action.triggered.connect(self.edit)

        # create context menu
        self.pop_menu = QtGui.QMenu(self)
        self.pop_menu.addAction(self.edit_action)

        # right clicking on the keyframe will bring up the context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        signal_str = 'customContextMenuRequested(const QPoint&)'
        self.connect(self, QtCore.SIGNAL(signal_str), self.onContextMenu)

    def generateToolTip(self):
        tt = fmt.b(fmt.red(self.ch_name)) + '<br>'
        tt += fmt.i(self.dct['comment']) + '<br>\n'
        tt += fmt.b(self.dct['id']) + '<br>\n'
        tt += '<br><i>right-click label to edit...</i>'
        self.setToolTip(tt)

    def edit(self):
        print('edit')

    def onContextMenu(self, point):
        # show context menu
        self.pop_menu.exec_(self.mapToGlobal(point))


class QChannelSegment(QtGui.QWidget):

    def __init__(self, dct, parent):
        super(QChannelSegment, self).__init__(parent)
        self.dct = dct
        self.vbox = QtGui.QVBoxLayout(self)
        self.setLayout(self.vbox)

        self.ramp_type_list = sorted(ramp_types.keys())
        self.curr_ramp_index = self.ramp_type_list.index(self.dct['ramp_type'])

        self.ramp_type_combo = QtGui.QComboBox(self)
        self.ramp_type_combo.addItems(sorted(ramp_types.keys()))
        self.ramp_type_combo.setCurrentIndex(self.curr_ramp_index)
        self.ramp_type_combo.currentIndexChanged.connect(self.handleRampTypeChanged)

        ramp_parm_names = ramp_types[self.dct['ramp_type']]
        self.spin_boxes = QMultipleSpinBoxEdit(ramp_parm_names, self)
        self.spin_boxes.valueChanged.connect(self.handleValueChanged)
        self.vbox.addWidget(self.ramp_type_combo)
        self.vbox.addWidget(self.spin_boxes)

    def handleRampTypeChanged(self, new_ramp_type_index):
        print(new_ramp_type_index)

    def handleValueChanged(self, new_values):
        print('new_values', new_values)


class QChannel(Channel):

    """Edits channels."""

    def __init__(self, ch_name, dct, key_frame_list, settings, grid, parent,
                 start_pos=(0, 0)):
        super(QChannel, self).__init__(ch_name, dct, key_frame_list)
        self.start_pos = start_pos
        self.parent = parent
        self.grid = grid
        self.setupUi()

    def setupUi(self):
        self.ch_info = QChannelInfoBox(self.ch_name, self.dct, self.parent)
        self.grid.addWidget(self.ch_info, self.start_pos[0], self.start_pos[1])
        # cycle through all keys keys in key list and find out which ones
        # we have in our channel
        self.ch_segments = []
        for i, key in enumerate(self.key_frame_list.sorted_key_list()):
            if key in self.dct['keys']:
                ch_seg = QChannelSegment(self.dct['keys'][key], self.parent)
                self.grid.addWidget(ch_seg, self.start_pos[0],
                                    self.start_pos[1] + i + 1)
                self.ch_segments.append(ch_seg)
            else:
                print('no la tengo')

        print('Creating channel')
