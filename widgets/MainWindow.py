from PyQt4 import uic
from PyQt4.QtGui import QFileDialog
from PyQt4 import QtGui
from widgets import RampEditor

Ui_MainWindow, QMainWindow = uic.loadUiType("ui/MainWindow.ui")


class MainWindow(QMainWindow, Ui_MainWindow):
    """Where all the action happens."""

    def __init__(self, settings):
        super(MainWindow, self).__init__()
        self.settings = settings
        self.setupUi(self)

        self.scrollArea = QtGui.QScrollArea(self)

        self.ramp_editor = RampEditor(settings)
        self.scrollArea.setWidget(self.ramp_editor)
        self.scrollArea.setWidgetResizable(True)
        self.is_saved = True  # change this whenever rampeditor makes changes
        self.setCentralWidget(self.scrollArea)
        self.loadSettings()

        self.ramp_editor.openNewFile(self.path_to_ramp_file)
        self.ramp_editor.ramp_changed.connect(self.rampChanged)
        self.setWindowTitle(self.path_to_ramp_file)

    def rampChanged(self):
        """Call this whenever the ramp is changed."""
        self.is_saved = False
        self.setWindowTitle(self.path_to_ramp_file + '*')

    def loadSettings(self):
        """Load window state from self.settings"""
        self.settings.beginGroup('mainwindow')
        geometry = self.settings.value('geometry').toByteArray()
        state = self.settings.value('windowstate').toByteArray()
        # dock_string = str(self.settings.value('dockstate').toString())
        # if dock_string is not "":
        #     dock_state = eval(dock_string)
        #     self.dock_area.restoreState(dock_state)

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
        def reallyClose(event):
            event.accept()
            self.saveSettings()
            super(MainWindow, self).closeEvent(event)

        # close if ramp has no changes
        if self.is_saved:
            reallyClose(event)
            return
        # else, ask if user wants to save file
        msg_str = "Save changes to current scene:" + self.path_to_ramp_file+"?"
        reply = QtGui.QMessageBox.warning(self, 'Unsaved Scene',
                                          msg_str,
                                          (QtGui.QMessageBox.Yes |
                                           QtGui.QMessageBox.No |
                                           QtGui.QMessageBox.Cancel),
                                          QtGui.QMessageBox.Yes)
        if reply == QtGui.QMessageBox.No:
            reallyClose(event)
        elif reply == QtGui.QMessageBox.Cancel:
            event.ignore()
        else:
            self.handleSave()
            reallyClose(event)

    def setWindowTitle(self, newTitle=''):
        """Prepend Rampage to all window titles."""
        title = 'Rampage - ' + newTitle
        super(MainWindow, self).setWindowTitle(title)

    def handleSave(self):
        self.ramp_editor.save(self.path_to_ramp_file)
        self.is_saved = True
        self.setWindowTitle(self.path_to_ramp_file)

    def handleSaveAs(self):
        fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Open file',
                    self.path_to_ramp_file))
        if fname != '':
            self.path_to_ramp_file = fname
            self.handleSave()

    def handleOpen(self):
        # save old opened file
        if not self.is_saved:
            msg_str = ("Save changes to current scene:"
                       + self.path_to_ramp_file+"?")
            reply = QtGui.QMessageBox.warning(self, 'Unsaved Scene',
                                              msg_str,
                                              (QtGui.QMessageBox.Yes |
                                               QtGui.QMessageBox.No |
                                               QtGui.QMessageBox.Cancel),
                                              QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.No:
                pass
            elif reply == QtGui.QMessageBox.Cancel:
                return
            else:
                self.handleSave()

        path_to_new_file = str(QFileDialog.getOpenFileName(self, "Open File",
                                                       self.path_to_ramp_file,
                                                       "Ramp files (*.json)"))

        if path_to_new_file is not '':
            self.path_to_ramp_file = path_to_new_file
            self.ramp_editor.openNewFile(self.path_to_ramp_file)
            self.setWindowTitle(self.path_to_ramp_file)
            self.is_saved = True
