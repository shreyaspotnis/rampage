# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore
from ..ramps import KeyFrameList
from CommonWidgets import MyDoubleSpinBox
import rampage.format as fmt
import rampage.server as server
from DictEditor import DictEditor

all_hooks_dict = dict(server.Hooks.default_mesgs)


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
    edit_hooks = QtCore.pyqtSignal()

    def __init__(self, key_name, kf, settings):
        super(QKeyFrame, self).__init__()
        self.settings = settings

        self.vbox = QtGui.QVBoxLayout(self)
        self.time_spin_box = MyDoubleSpinBox(self)
        self.name_label = QtGui.QLabel(self)
        self.abs_time_label = QtGui.QLabel(self)

        self.setFocusProxy(self.time_spin_box)

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

        # create hook menu
        self.hook_menu = QtGui.QMenu('Hooks', self)
        self.add_hook_menu = QtGui.QMenu('Add', self)
        self.edit_hook_menu = QtGui.QMenu('Edit', self)
        self.del_hook_menu = QtGui.QMenu('Delete', self)
        self.hook_menu.addMenu(self.add_hook_menu)
        self.hook_menu.addMenu(self.edit_hook_menu)
        self.hook_menu.addMenu(self.del_hook_menu)
        # create context menu
        self.pop_menu = QtGui.QMenu(self)
        self.pop_menu.addAction(self.edit_action)
        self.pop_menu.addAction(self.insert_action)
        self.pop_menu.addAction(self.add_action)
        self.pop_menu.addSeparator()
        self.pop_menu.addMenu(self.hook_menu)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.delete_action)

        # right clicking on the keyframe will bring up the context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        signal_str = 'customContextMenuRequested(const QPoint&)'
        self.connect(self, QtCore.SIGNAL(signal_str), self.onContextMenu)

    def update(self, key_name, kf):
        # disconnect slot before updating, reconnect at the end.

        self.key_name = key_name
        self.kf = kf
        self.updateUI()

    def updateUI(self):
        self.time_spin_box.valueChanged.disconnect(self.handleTimeChanged)
        self.time_spin_box.setValue(self.kf['time'])
        self.abs_time_label.setText(str(self.kf['__abs_time__']))
        self.generateToolTip()
        if 'hooks' in self.kf:
            print(len(self.kf['hooks']))
            add_hook_symbol = len(self.kf['hooks']) > 0
        else:
            add_hook_symbol = False
        if add_hook_symbol:
            self.name_label.setText(fmt.b(fmt.red(self.key_name+' !')))
        else:
            self.name_label.setText(fmt.b(fmt.red(self.key_name)))
        self.time_spin_box.valueChanged.connect(self.handleTimeChanged)

    def generateToolTip(self):
        tt = 'Name: ' + fmt.b(fmt.red(self.key_name)) + '<br>\n'
        tt += 'Comment: ' + fmt.i(self.kf['comment']) + '<br>\n'
        if self.kf['parent'] is not None:
            tt += 'Parent: ' + fmt.b(fmt.red(self.kf['parent']))
        else:
            tt += 'Parent: ' + fmt.b(fmt.red("None"))
        tt += '<br>Abs. Time: ' + str(self.kf['__abs_time__'])

        # get info on hooks
        tt += '<br> Hooks: '
        if 'hooks' not in self.kf:
            tt += 'None'
        else:
            l = list(self.kf['hooks'].iterkeys())
            if len(l) is 0:
                tt += 'None'
            else:
                tt += ', '.join(l)
        tt += '<br><i>right-click label to edit...</i>'
        self.setToolTip(tt)

    def onContextMenu(self, point):
        # show context menu
        self.add_hook_menu.clear()
        for hook_name in all_hooks_dict.iterkeys():
            action = self.add_hook_menu.addAction(hook_name)
            action.triggered[()].connect(lambda x=hook_name: self.addHook(x))
        self.edit_hook_menu.clear()
        if 'hooks' in self.kf:
            for hook_name in self.kf['hooks'].iterkeys():
                action = self.edit_hook_menu.addAction(hook_name)
                action.triggered[()].connect(lambda x=hook_name: self.editHook(x))

        self.edit_hook_menu.clear()
        self.del_hook_menu.clear()
        if 'hooks' in self.kf:
            for hook_name in self.kf['hooks'].iterkeys():
                action = self.edit_hook_menu.addAction(hook_name)
                action.triggered[()].connect(lambda x=hook_name: self.addHook(x))
                action = self.del_hook_menu.addAction(hook_name)
                action.triggered[()].connect(lambda x=hook_name: self.delHook(x))

        self.pop_menu.exec_(self.mapToGlobal(point))

    def addHook(self, hook_name):
        hook_name = str(hook_name)
        print('ADDING', hook_name)
        print(all_hooks_dict[hook_name])
        # if hook is already added, then edit it
        if 'hooks' in self.kf:
            if hook_name in self.kf['hooks']:
                data_dict = dict(self.kf['hooks'][hook_name])
            else:
                data_dict = dict(all_hooks_dict[hook_name])
        else:
            data_dict = dict(all_hooks_dict[hook_name])
        dct_editor = DictEditor(data_dict, hook_name)
        if dct_editor.exec_():
            if 'hooks' not in self.kf:
                self.kf['hooks'] = {}
            self.kf['hooks'][hook_name] = data_dict
            self.updateUI()
            self.edit_hooks.emit()

    def delHook(self, hook_name):
        # else, ask if user wants to save file
        msg_str = "Really delete hook:" + hook_name+"?"
        reply = QtGui.QMessageBox.warning(self, 'Delete hook',
                                          msg_str,
                                          (QtGui.QMessageBox.Yes |
                                           QtGui.QMessageBox.No),
                                          QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.kf['hooks'].pop(hook_name)
            self.updateUI()
            self.edit_hooks.emit()

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


class QArrowWidget(QtGui.QLabel):

    """Responsible for drawing arrows which show parent child relationship."""

    def __init__(self, arrow_list, grid, start_pos=(0, 0), parent=None):
        super(QArrowWidget, self).__init__(parent)
        self.grid = grid
        self.start_pos = start_pos
        self.grid.addWidget(self, self.start_pos[0], self.start_pos[1], 1, -1)
        self.figureOutHowToDrawArrows(arrow_list)
        self.setSizePolicy(QtGui.QSizePolicy.Ignored,
                           QtGui.QSizePolicy.Fixed)

    def sizeHint(self):
        return QtCore.QSize(1000, (self.max_height+1)*10+5)

    def figureOutHowToDrawArrows(self, arrow_list):
        n_cols = 0
        for arrow in arrow_list:
            n_cols = max(max(n_cols, arrow[0]), arrow[1])
        self.n_cols = n_cols + 1

        self.arrow_list = arrow_list

        availability = []
        self.height_list = []
        for arrow in arrow_list:
            left_index = min(arrow[0], arrow[1])
            right_index = max(arrow[0], arrow[1])
            used = [False]*(right_index - left_index)
            for i, avail in enumerate(availability):
                if all(avail[left_index:right_index]):
                    height = i
                    break
            else:
                height = len(availability)
                availability.append([True]*self.n_cols)
            availability[height][left_index:right_index] = used
            self.height_list.append(height)
        self.max_height = len(availability)

    def paintEvent(self, event):
        centers = []
        r = self.grid.cellRect(self.start_pos[0], self.start_pos[1])
        top_left = r.topLeft()
        for i in range(self.n_cols):
            r = self.grid.cellRect(self.start_pos[0], i+self.start_pos[1])
            c = r.bottomRight() - top_left
            centers.append(c)

        qp = QtGui.QPainter()
        qp.begin(self)
        for arrow, height in zip(self.arrow_list, self.height_list):
            center_left = centers[arrow[0]]
            center_right = centers[arrow[1]]
            hp = 10*height + 5

            def drawArrow(qp, x1, x2, height):
                length = 5
                qp.drawLine(x1, height, x2, height)
                qp.drawLine(x1, height - length, x1, height + length)
                brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
                qp.setBrush(brush)
                if x1 > x2:
                    length = -5
                points = [QtCore.QPoint(x2, height),
                          QtCore.QPoint(x2-length, height-length),
                          QtCore.QPoint(x2-length, height+length)]
                arrowHead = QtGui.QPolygon(points)
                qp.drawPolygon(arrowHead)

            drawArrow(qp, center_left.x(), center_right.x(), hp)
        qp.end()


class QKeyFrameList(KeyFrameList):

    """Gui for editing key frames."""

    def __init__(self, dct, settings, grid, start_pos=(0, 0),
                 parent_widget=None, set_focus_on=None):
        super(QKeyFrameList, self).__init__(dct)
        self.settings = settings
        self.start_pos = start_pos
        self.grid = grid
        self.parent_widget = parent_widget
        self.set_focus_on = set_focus_on
        self.setupUi(self)

    def setupUi(self, widget):
        self.kf_list = []
        skl = self.sorted_key_list()
        for i, key in enumerate(skl):
            kf = self.createNewKeyFrameWidget(key, self.dct[key])

            self.grid.addWidget(kf, self.start_pos[0], self.start_pos[1] + i)
            self.kf_list.append(kf)

        arrow_start = self.start_pos[0] + 1, self.start_pos[1]
        self.arrow_widget = QArrowWidget(self.getArrowList(), self.grid,
                                         start_pos=arrow_start,
                                         parent=self.parent_widget)
        if self.set_focus_on is not None:
            index = skl.index(self.set_focus_on)
            self.kf_list[index].setFocus()

    def getArrowList(self):
        arrow_list = []
        skl = self.sorted_key_list()
        for i, key in enumerate(skl):
            right_index = i
            if self.dct[key]['parent'] is None:
                continue
            else:
                left_index = skl.index(self.dct[key]['parent'])
            arrow = (left_index, right_index)
            arrow_list.append(arrow)
        return arrow_list

    def createNewKeyFrameWidget(self, key_name, key_dict):
        kf = QKeyFrame(key_name, key_dict, self.settings)
        kf.edit_signal.connect(self.handleEdit)
        kf.delete_signal.connect(self.handleDelete)
        kf.insert_before_signal.connect(self.handleInsertBefore)
        kf.add_child_signal.connect(self.handleAddChild)
        kf.time_changed_signal.connect(self.handleTimeChanged)
        kf.edit_hooks.connect(self.handleEditHooks)
        return kf

    def disconnectKeyFrame(self, kf):
        # disconnect all signals
        kf.edit_signal.disconnect(self.handleEdit)
        kf.delete_signal.disconnect(self.handleDelete)
        kf.insert_before_signal.disconnect(self.handleInsertBefore)
        kf.add_child_signal.disconnect(self.handleAddChild)
        kf.time_changed_signal.disconnect(self.handleTimeChanged)

    def handleEditHooks(self):
        self.parent_widget.ramp_changed.emit()

    def handleTimeChanged(self, key_name, new_time):
        skl_old = self.sorted_key_list()
        self.set_time(key_name, new_time)
        skl_new = self.sorted_key_list()
        # check if the order of keyframes has changed
        order_changed = False
        for kold, knew in zip(skl_old, skl_new):
            if kold != knew:
                order_changed = True
                break
        if order_changed:
            for kf in self.kf_list:
                self.disconnectKeyFrame(kf)
            print('Re do ui')
            self.parent_widget.reDoUi(set_focus_on=key_name)
        else:
            self.parent_widget.ramp_changed.emit()
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
            if key_name != new_key_name:
                self.set_name(key_name, new_key_name)
                self.parent_widget.handleKeyNameChanged(key_name, new_key_name)
            for kf in self.kf_list:
                self.disconnectKeyFrame(kf)
            self.parent_widget.reDoUi()

    def handleInsertBefore(self, key_name):
        new_key_name, ok = QtGui.QInputDialog.getText(self.parent_widget,
                                                      'Add child',
                                                      'Enter key name:')
        if ok:
            parent_key = self.dct[key_name]['parent']
            kf = {'time': 1.0, 'parent': parent_key, "comment": "comment"}
            self.dct[key_name]['parent'] = str(new_key_name)
            self.add_keyframe(str(new_key_name), kf)

            for kf in self.kf_list:
                self.disconnectKeyFrame(kf)
            self.parent_widget.reDoUi()

    def handleAddChild(self, key_name):
        new_key_name, ok = QtGui.QInputDialog.getText(self.parent_widget,
                                                      'Add child',
                                                      'Enter key name:')
        if ok:
            kf = {'time': 1.0, 'parent': key_name, "comment": "comment"}
            self.add_keyframe(str(new_key_name), kf)
            for kf in self.kf_list:
                self.disconnectKeyFrame(kf)
            self.parent_widget.reDoUi()

    def handleDelete(self, key_name):
        self.del_keyframe(key_name)
        for kf in self.kf_list:
            self.disconnectKeyFrame(kf)
        self.parent_widget.reDoUi()

    def updateAllKeys(self):
        """Update times for all keys in the layout."""
        for kf, key in zip(self.kf_list, self.sorted_key_list()):
            kf.update(key, self.dct[key])
