from PyQt4 import QtGui, QtCore
from ramps import KeyFrameList
import format as fmt
import json


class QEditKeyFrameDialog(QtGui.QDialog):

    def __init__(self, key_name, kf, parent_list, disabled_list, parent):
        super(QEditKeyFrameDialog, self).__init__(parent)

        self.setWindowTitle('Edit keyframe')
        self.text_name = QtGui.QLineEdit(key_name, self)
        self.text_comment = QtGui.QLineEdit(kf['comment'], self)

        self.button_ok = QtGui.QPushButton('Ok', self)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel = QtGui.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.reject)
        self.button_ok.clicked.connect(self.accept)

        self.combo_parent = QtGui.QComboBox(self)
        self.combo_parent.addItem('None')
        self.combo_parent.addItems(parent_list)
        if kf['parent'] is None:
            self.current_parent_index = 0  # assume no parent
        else:
            self.current_parent_index = parent_list.index(kf['parent']) + 1

        self.combo_parent.setCurrentIndex(self.current_parent_index)

        self.grid = QtGui.QGridLayout(self)
        self.grid.addWidget(QtGui.QLabel('Name'), 0, 0)
        self.grid.addWidget(self.text_name, 0, 1)
        self.grid.addWidget(QtGui.QLabel('Comment'), 1, 0)
        self.grid.addWidget(self.text_comment, 1, 1)
        parent_string = 'Parent (current: ' + str(kf['parent']) + ')'

        self.grid.addWidget(QtGui.QLabel(parent_string), 2, 0)
        self.grid.addWidget(self.combo_parent)
        self.grid.addWidget(self.button_ok, 3, 0)
        self.grid.addWidget(self.button_cancel, 3, 1)
        self.setLayout(self.grid)

        for i, is_disabled in enumerate(disabled_list):
            if is_disabled:
                j = self.combo_parent.model().index(i + 1, 0)
                self.combo_parent.model().setData(j, QtCore.QVariant(0),
                                                 QtCore.Qt.UserRole-1)
        self.kf = kf
        self.key_name = key_name
        self.parent_list = parent_list

    def exec_(self):
        execReturn = super(QEditKeyFrameDialog, self).exec_()
        name = str(self.text_name.text())
        comment = str(self.text_comment.text())
        parent_string = str(self.combo_parent.currentText())
        return execReturn, name, comment, parent_string


class QKeyFrame(QtGui.QWidget):

    """GUI for an individual keyframe.

    Disylays and can edit time, comments, parent of keyframes."""

    edit_signal = QtCore.pyqtSignal(object)
    delete_signal = QtCore.pyqtSignal(object)
    insert_before_signal = QtCore.pyqtSignal(object)
    add_child_signal = QtCore.pyqtSignal(object)
    time_changed_signal = QtCore.pyqtSignal(object, object)

    def __init__(self, key_name, kf, settings):
        super(QKeyFrame, self).__init__()
        self.settings = settings

        self.vbox = QtGui.QVBoxLayout(self)
        self.time_spin_box = QtGui.QDoubleSpinBox(self)
        self.name_label = QtGui.QLabel(self)
        self.abs_time_label = QtGui.QLabel(self)

        for w in [self.name_label, self.abs_time_label, self.time_spin_box]:
            w.setAlignment(QtCore.Qt.AlignRight)
            self.vbox.addWidget(w)

        self.setLayout(self.vbox)

        self.time_spin_box.setKeyboardTracking(False)
        self.time_spin_box.valueChanged.connect(self.handleTimeChanged)

        # TODO: see if these numbers need to be changed in settings
        self.time_spin_box.setDecimals(3)
        self.time_spin_box.setMaximum(1e5)
        self.time_spin_box.setMinimum(-1e5)

        self.update(key_name, kf)

        # create actions to edit the keyframe
        self.edit_action = QtGui.QAction('&Edit', self)
        self.insert_action = QtGui.QAction('&Insert Before', self)
        self.add_action = QtGui.QAction('&Add child', self)
        self.delete_action = QtGui.QAction('Delete', self)

        # connect actions to slots
        self.edit_action.triggered.connect(self.edit)
        self.insert_action.triggered.connect(self.insert)
        self.add_action.triggered.connect(self.add)
        self.delete_action.triggered.connect(self.delete)

        # create context menu
        self.pop_menu = QtGui.QMenu(self)
        self.pop_menu.addAction(self.edit_action)
        self.pop_menu.addAction(self.insert_action)
        self.pop_menu.addAction(self.add_action)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.delete_action)

        # right clicking on the keyframe will bring up the context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        signal_str = 'customContextMenuRequested(const QPoint&)'
        self.connect(self, QtCore.SIGNAL(signal_str), self.onContextMenu)

    def update(self, key_name, kf):
        # disconnect slot before updating, reconnect at the end.
        self.time_spin_box.valueChanged.disconnect(self.handleTimeChanged)

        self.key_name = key_name
        self.kf = kf
        self.time_spin_box.setValue(self.kf['time'])
        self.name_label.setText(fmt.b(fmt.red(self.key_name)))
        self.abs_time_label.setText(str(self.kf['__abs_time__']))
        self.generateToolTip()

        self.time_spin_box.valueChanged.connect(self.handleTimeChanged)

    def generateToolTip(self):
        tt = 'Name: ' + fmt.b(fmt.red(self.key_name)) + '<br>'
        tt += 'Comment: ' + fmt.i(self.kf['comment']) + '<br>\n'
        if self.kf['parent'] is not None:
            tt += 'Parent: ' + fmt.b(fmt.red(self.kf['parent']))
        else:
            tt += 'Parent: ' + fmt.b(fmt.red("None"))
        tt += '<br>Abs. Time: ' + str(self.kf['__abs_time__'])
        tt += '<br><i>right-click label to edit...</i>'
        self.setToolTip(tt)

    def onContextMenu(self, point):
        # show context menu
        self.pop_menu.exec_(self.mapToGlobal(point))

    def edit(self):
        self.edit_signal.emit(self.key_name)

    def insert(self):
        self.insert_before_signal.emit(self.key_name)

    def add(self):
        self.add_child_signal.emit(self.key_name)

    def delete(self):
        self.delete_signal.emit(self.key_name)

    def handleTimeChanged(self, new_time):
        self.time_changed_signal.emit(self.key_name, float(new_time))


class QKeyFrameList(KeyFrameList):

    """Gui for editing key frames."""

    def __init__(self, dct, settings, grid, start_pos=(0, 0),
                 parent_widget=None):
        super(QKeyFrameList, self).__init__(dct)
        self.settings = settings
        self.start_pos = start_pos
        self.grid = grid
        self.parent_widget = parent_widget
        self.setupUi(self)

    def setupUi(self, widget):
        self.kf_list = []
        for i, key in enumerate(self.sorted_key_list()):
            kf = self.createNewKeyFrameWidget(key, self.dct[key])

            self.grid.addWidget(kf, self.start_pos[0], self.start_pos[1] + i)
            self.kf_list.append(kf)

    def createNewKeyFrameWidget(self, key_name, key_dict):
        kf = QKeyFrame(key_name, key_dict, self.settings)
        kf.edit_signal.connect(self.handleEdit)
        kf.delete_signal.connect(self.handleDelete)
        kf.insert_before_signal.connect(self.handleInsertBefore)
        kf.add_child_signal.connect(self.handleAddChild)
        kf.time_changed_signal.connect(self.handleTimeChanged)
        return kf

    def handleTimeChanged(self, key_name, new_time):
        self.set_time(key_name, new_time)
        self.updateAllKeys()

    def handleEdit(self, key_name):
        # find out all keys which are descendents of key_name
        disabled_list = [self.is_ancestor(k, key_name) for k in
                         self.sorted_key_list()]
        out_tuple = QEditKeyFrameDialog(key_name,
                                        self.dct[key_name],
                                        self.sorted_key_list(),
                                        disabled_list,
                                        None).exec_()
        exec_return, new_key_name, new_comment, new_parent = out_tuple
        if exec_return == QtGui.QDialog.Accepted:
            self.dct[key_name]['comment'] = new_comment
            if new_parent == 'None':
                new_parent = None
            self.set_parent(key_name, new_parent)
            self.set_name(key_name, new_key_name)
            self.updateAllKeys()

    def handleInsertBefore(self, key_name):
        new_key_name, ok = QtGui.QInputDialog.getText(self.parent_widget,
                                                      'Add child',
                                                      'Enter key name:')
        if ok:
            parent_key = self.dct[key_name]['parent']
            kf = {'time': 1.0, 'parent': parent_key, "comment": "comment"}
            self.dct[key_name]['parent'] = str(new_key_name)
            self.add_keyframe(str(new_key_name), kf)
            kf_gui = self.createNewKeyFrameWidget(key_name, self.dct[key_name])
            self.kf_list.append(kf_gui)
            self.grid.addWidget(kf_gui, self.start_pos[0], self.start_pos[1]
                                + len(self.kf_list))
            self.updateAllKeys()

    def handleAddChild(self, key_name):
        new_key_name, ok = QtGui.QInputDialog.getText(self.parent_widget,
                                                      'Add child',
                                                      'Enter key name:')
        if ok:
            kf = {'time': 1.0, 'parent': key_name, "comment": "comment"}
            self.add_keyframe(str(new_key_name), kf)
            kf_gui = self.createNewKeyFrameWidget(key_name, self.dct[key_name])
            self.kf_list.append(kf_gui)
            self.grid.addWidget(kf_gui, self.start_pos[0], self.start_pos[1]
                                + len(self.kf_list))
            self.updateAllKeys()

    def handleDelete(self, key_name):
        self.del_keyframe(key_name)
        # remove the last widget from the list
        kf_del = self.kf_list.pop()
        # disconnect all signals
        kf_del.edit_signal.disconnect(self.handleEdit)
        kf_del.delete_signal.disconnect(self.handleDelete)
        kf_del.insert_before_signal.disconnect(self.handleInsertBefore)
        kf_del.add_child_signal.disconnect(self.handleAddChild)
        kf_del.time_changed_signal.disconnect(self.handleTimeChanged)

        self.grid.removeWidget(kf_del)
        kf_del.deleteLater()

        self.updateAllKeys()

    def updateAllKeys(self):
        # update key frames GUI
        for kf, key in zip(self.kf_list, self.sorted_key_list()):
            kf.update(key, self.dct[key])


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
        self.kfl = QKeyFrameList(data['keyframes'], self.settings, self.grid,
                                 start_pos=(0, 0), parent_widget=self)
