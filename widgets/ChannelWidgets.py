from PyQt4 import QtGui, QtCore
from ramps import Channel, ramp_types
from widgets.CommonWidgets import QMultipleSpinBoxEdit
import format as fmt


class QEditChannelInfoDialog(QtGui.QDialog):

    def __init__(self, ch_name, dct, parent):
        super(QEditChannelInfoDialog, self).__init__(parent)

        self.setWindowTitle('Edit channel info')
        self.text_name = QtGui.QLineEdit(ch_name, self)
        self.text_comment = QtGui.QLineEdit(dct['comment'], self)
        self.text_id = QtGui.QLineEdit(dct['id'], self)

        self.button_ok = QtGui.QPushButton('Ok', self)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel = QtGui.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.reject)
        self.button_ok.clicked.connect(self.accept)

        self.grid = QtGui.QGridLayout(self)
        self.grid.addWidget(QtGui.QLabel('Name'), 0, 0)
        self.grid.addWidget(self.text_name, 0, 1)
        self.grid.addWidget(QtGui.QLabel('Comment'), 1, 0)
        self.grid.addWidget(self.text_comment, 1, 1)
        self.grid.addWidget(QtGui.QLabel('id'), 2, 0)
        self.grid.addWidget(self.text_id, 2, 1)

        self.grid.addWidget(self.button_ok, 3, 0)
        self.grid.addWidget(self.button_cancel, 3, 1)
        self.setLayout(self.grid)

        self.dct = dct
        self.ch_name = ch_name

    def exec_(self):
        execReturn = super(QEditChannelInfoDialog, self).exec_()
        name = str(self.text_name.text())
        comment = str(self.text_comment.text())
        id_string = str(self.text_id.text())
        return execReturn, name, comment, id_string


class QChannelInfoBox(QtGui.QWidget):

    """Displays channel name, comment and other info."""

    edit_signal = QtCore.pyqtSignal(object)

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
        self.edit_signal.emit(self.ch_name)

    def onContextMenu(self, point):
        # show context menu
        self.pop_menu.exec_(self.mapToGlobal(point))

    def edit_channel_info(self, new_ch_name, ch_dct):
        self.ch_name = new_ch_name
        self.dct = ch_dct
        self.ch_name_label.setText(fmt.b(fmt.green(self.ch_name)))
        self.generateToolTip()


class QChannelSegment(QtGui.QWidget):

    delete_segment = QtCore.pyqtSignal(object)
    edit_segment = QtCore.pyqtSignal()

    def __init__(self, keyname, dct, parent):
        super(QChannelSegment, self).__init__(parent)
        self.dct = dct
        self.vbox = QtGui.QVBoxLayout(self)
        self.setLayout(self.vbox)
        self.keyname = keyname

        self.ramp_type_list = sorted(ramp_types.keys())
        self.curr_ramp_index = self.ramp_type_list.index(self.dct['ramp_type'])

        self.ramp_type_combo = QtGui.QComboBox(self)
        self.ramp_type_combo.addItems(sorted(ramp_types.keys()))
        self.ramp_type_combo.insertSeparator(len(ramp_types))
        self.ramp_type_combo.addItem('delete')
        self.ramp_type_combo.setCurrentIndex(self.curr_ramp_index)
        self.ramp_type_combo.currentIndexChanged.connect(self.handleRampTypeChanged)

        ramp_parm_names = sorted(ramp_types[self.dct['ramp_type']])
        ramp_parm_values = [self.dct['ramp_data'][k] for k in ramp_parm_names]
        self.spin_boxes = QMultipleSpinBoxEdit(ramp_parm_names, self,
                                               ramp_parm_values)
        self.spin_boxes.valueChanged.connect(self.handleValueChanged)
        self.vbox.addWidget(self.ramp_type_combo)
        self.vbox.addWidget(self.spin_boxes)

    def handleRampTypeChanged(self, new_ramp_type_index):
        print(new_ramp_type_index)
        item_text = str(self.ramp_type_combo.itemText(new_ramp_type_index))
        if item_text == 'delete':
            self.delete_segment.emit(self.keyname)
        else:
            ramp_parm_names = ramp_types[item_text]
            self.spin_boxes.editAttributes(ramp_parm_names)
            self.dct['ramp_type'] = item_text
            ramp_data_dct = {}
            for rpn in ramp_parm_names:
                ramp_data_dct[rpn] = 0.0
            self.dct['ramp_data'] = ramp_data_dct
            self.edit_segment.emit()

    def handleValueChanged(self, new_values):
        print('new_values', new_values)


class QChannel(Channel):

    """Edits channels.

    parent widget should have the following slots:

    handleEditChannelInfo(self, ch_name)
    """

    def __init__(self, ch_name, dct, key_frame_list, settings, grid, parent,
                 start_pos=(0, 0)):
        super(QChannel, self).__init__(ch_name, dct, key_frame_list)
        self.start_pos = start_pos
        self.parent = parent
        self.grid = grid
        self.setupUi()

    def setupUi(self):
        self.ch_info = QChannelInfoBox(self.ch_name, self.dct, self.parent)
        self.ch_info.edit_signal.connect(self.parent.handleEditChannelInfo)
        self.grid.addWidget(self.ch_info, self.start_pos[0], self.start_pos[1])
        # cycle through all keys keys in key list and find out which ones
        # we have in our channel
        self.ch_segments = []
        for i, key in enumerate(self.key_frame_list.sorted_key_list()):
            if key in self.dct['keys']:
                ch_seg = QChannelSegment(key, self.dct['keys'][key],
                                         self.parent)
                ch_seg.delete_segment.connect(self.handleDeleteSegment)
                # evil hack
                ch_seg.edit_segment.connect(self.parent.ramp_changed)
                self.grid.addWidget(ch_seg, self.start_pos[0],
                                    self.start_pos[1] + i + 1)
                self.ch_segments.append(ch_seg)
            else:
                print('no la tengo')

        print('Creating channel')

    def edit_channel_info(self, new_ch_name, ch_dct):
        self.set_name(new_ch_name)
        self.dct = ch_dct
        self.ch_info.edit_channel_info(new_ch_name, ch_dct)

    def handleDeleteSegment(self, keyname):
        index = -1
        for i, ch_seg in enumerate(self.ch_segments):
            if ch_seg.keyname == keyname:
                index = i
        if index is not -1:
            ch_del = self.ch_segments.pop(index)
            self.grid.removeWidget(ch_del)
            ch_del.deleteLater()
            self.dct['keys'].pop(keyname)
            # evil hack follows
            self.parent.ramp_changed.emit()


