from PyQt4 import QtGui, QtCore
from ramps import KeyFrameList
import format as fmt
import json


class QKeyFrame(QtGui.QWidget):

    """GUI for an individual keyframe.

    Disylays and can edit time, comments, parent of keyframes."""

    def __init__(self, key_name, kf, settings):
        super(QKeyFrame, self).__init__()
        self.kf = kf
        self.key_name = key_name
        self.settings = settings

        self.vbox = QtGui.QVBoxLayout(self)
        self.time_spin_box = QtGui.QDoubleSpinBox(self)
        self.name_label = QtGui.QLabel(fmt.b(fmt.red(self.key_name)), self)
        self.abs_time_label = QtGui.QLabel(str(self.kf['__abs_time__']), self)

        for w in [self.name_label, self.abs_time_label, self.time_spin_box]:
            w.setAlignment(QtCore.Qt.AlignRight)
            self.vbox.addWidget(w)

        self.setLayout(self.vbox)

        self.time_spin_box.setValue(self.kf['time'])

        # TODO: see if these numbers need to be changed in settings
        self.time_spin_box.setDecimals(3)
        self.time_spin_box.setMaximum(1e5)
        self.time_spin_box.setMinimum(-1e5)

        # create actions to edit the keyframe
        self.editAction = QtGui.QAction('&Edit', self)
        self.insertAction = QtGui.QAction('&Insert Before', self)
        self.addAction = QtGui.QAction('&Add child', self)
        self.deleteAction = QtGui.QAction('Delete', self)

        # connect actions to slots
        self.editAction.triggered.connect(self.edit)
        self.insertAction.triggered.connect(self.insert)
        self.addAction.triggered.connect(self.add)
        self.deleteAction.triggered.connect(self.delete)

        # create context menu
        self.pop_menu = QtGui.QMenu(self)
        self.pop_menu.addAction(self.editAction)
        self.pop_menu.addAction(self.insertAction)
        self.pop_menu.addAction(self.addAction)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.deleteAction)

        # right clicking on the keyframe will bring up the context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self,
                     QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'),
                     self.onContextMenu)

    def onContextMenu(self, point):
        # show context menu
        self.pop_menu.exec_(self.mapToGlobal(point))

    def edit(self):
        print('edit')

    def insert(self):
        print('insert')

    def add(self):
        print('add')

    def delete(self):
        print('delete')


class QKeyFrameList(KeyFrameList):

    """Gui for editing key frames."""

    def __init__(self, dct, settings, grid, start_pos=(0, 0)):
        super(QKeyFrameList, self).__init__(dct)
        self.settings = settings
        self.start_pos = start_pos
        self.grid = grid
        self.setupUi(self)

    def setupUi(self, widget):
        for i, key in enumerate(self.sorted_key_list()):
            kf = QKeyFrame(key, self.dct[key], self.settings)
            self.grid.addWidget(kf, self.start_pos[0], self.start_pos[1] + i)


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
                                 start_pos=(0, 0))
