from PyQt4 import uic
from PyQt4.QtGui import QFileDialog
from widgets import RampEditor

Ui_MainWindow, QMainWindow = uic.loadUiType("ui/MainWindow.ui")


class MainWindow(QMainWindow, Ui_MainWindow):
    """Where all the action happens."""

    def __init__(self, settings):
        super(MainWindow, self).__init__()
        self.settings = settings
        self.setupUi(self)

        self.ramp_editor = RampEditor(settings)
        self.setCentralWidget(self.ramp_editor)
        self.loadSettings()

        self.ramp_editor.openNewFile(self.path_to_ramp_file)
        self.setWindowTitle(self.path_to_ramp_file)

    def loadSettings(self):
        """Load window state from self.settings"""
        self.settings.beginGroup('mainwindow')
        geometry = self.settings.value('geometry').toByteArray()
        state = self.settings.value('windowstate').toByteArray()
        dock_string = str(self.settings.value('dockstate').toString())
        if dock_string is not "":
            dock_state = eval(dock_string)
            self.dock_area.restoreState(dock_state)

        self.path_to_ramp_file = str(self.settings.value('path_to_ramp_file',
                                        'examples/test_scene.json').toString())
        self.settings.endGroup()

        self.restoreGeometry(geometry)
        self.restoreState(state)

    def saveSettings(self):
        """Save window state to self.settings."""
        self.settings.beginGroup('mainwindow')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowstate', self.saveState())
        self.settings.setValue('path_to_ramp_file', self.path_to_ramp_file)
        self.settings.endGroup()

    def closeEvent(self, event):
        self.saveSettings()
        super(MainWindow, self).closeEvent(event)

    def setWindowTitle(self, newTitle=''):
        """Prepend Rampage to all window titles."""
        title = 'Rampage - ' + newTitle
        super(MainWindow, self).setWindowTitle(title)

    def handleSave(self):
        self.ramp_editor.save(self.path_to_ramp_file)

    def handleSaveAs(self):
        print('saving as')

    def handleOpen(self):
        path_to_new_file = str(QFileDialog.getOpenFileName(self, "Open File",
                                                       self.path_to_ramp_file,
                                                       "Ramp files (*.json)"))
        if path_to_new_file is not '':
            self.path_to_ramp_file = path_to_new_file
            self.ramp_editor.openNewFile(self.path_to_ramp_file)
            self.setWindowTitle(self.path_to_ramp_file)