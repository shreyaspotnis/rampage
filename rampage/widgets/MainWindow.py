from PyQt4 import uic
from PyQt4.QtGui import QFileDialog
from PyQt4 import QtGui, QtCore
import os

from RampEditor import RampEditor
from rampage import queuer

main_package_dir = os.path.join(os.path.dirname(__file__), os.pardir)
ui_filename = os.path.join(main_package_dir, "ui/MainWindow.ui")
Ui_MainWindow, QMainWindow = uic.loadUiType(ui_filename)


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
        self.ramp_editor.setScrollWidget(self.scrollArea)
        self.setWindowTitle(self.path_to_ramp_file)

        self.overlay = Overlay(self.ramp_editor, self.scrollArea)

        self.show_overlay = False

    def resizeEvent(self, event):
        self.overlay.resize(event.size())
        event.accept()

    def rampChanged(self):
        """Call this whenever the ramp is changed."""
        self.is_saved = False
        self.setWindowTitle(self.path_to_ramp_file + '*')

    def loadSettings(self):
        """Load window state from self.settings"""
        self.settings.beginGroup('mainwindow')
        geometry = self.settings.value('geometry').toByteArray()
        state = self.settings.value('windowstate').toByteArray()

        default_ramp_path = os.path.join(main_package_dir,
                                         'examples/test_scene.json')

        self.path_to_ramp_file = str(self.settings.value('path_to_ramp_file',
                                     default_ramp_path).toString())
        self.path_to_load_mot_file = str(self.settings.value('path_to_load_mot_file',
                                         default_ramp_path).toString())
        if not os.path.isfile(self.path_to_ramp_file):
            self.path_to_ramp_file = default_ramp_path
        self.settings.endGroup()

        self.restoreGeometry(geometry)
        self.restoreState(state)

    def saveSettings(self):
        """Save window state to self.settings."""
        self.settings.beginGroup('mainwindow')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowstate', self.saveState())
        self.settings.setValue('path_to_ramp_file', self.path_to_ramp_file)
        self.settings.setValue('path_to_load_mot_file',
                               self.path_to_load_mot_file)
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

    def handleToggleOverlay(self):
        self.show_overlay = not self.show_overlay
        self.overlay.setShowOverlay(self.show_overlay)

    def handleCheckForErrors(self):
        self.ramp_editor.checkForErrors()

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

    def handleRunCurrent(self):
        error_list = self.ramp_editor.checkForErrors()
        all_errors = '\n'.join(error_list)

        if len(error_list) > 0:
            reply = QtGui.QMessageBox.warning(self, 'Errors in ramp. Continue?',
                                              all_errors,
                                              (QtGui.QMessageBox.Yes |
                                               QtGui.QMessageBox.No),
                                              QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return

        if not self.is_saved:
            msg_str = ("Do you want to save changes? Unsaved changes won't be uploaded. File:"
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

        queuer.run_ramp_immediately(self.path_to_ramp_file, self.settings)

    def handleRunWithLoadMot(self):
        error_list = self.ramp_editor.checkForErrors()
        all_errors = '\n'.join(error_list)

        if len(error_list) > 0:
            reply = QtGui.QMessageBox.warning(self, 'Errors in ramp. Continue?',
                                              all_errors,
                                              (QtGui.QMessageBox.Yes |
                                               QtGui.QMessageBox.No),
                                              QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return

        if not self.is_saved:
            msg_str = ("Do you want to save changes? Unsaved changes won't be uploaded. File:"
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
        queuer.queue_ramp_pair(self.path_to_load_mot_file,
                               self.path_to_ramp_file,
                               self.settings)

    def handleChangeLoadMotFile(self):
        # save old opened file
        fname = QFileDialog.getOpenFileName
        path_to_new_file = str(fname(self, "Open File",
                                     self.path_to_load_mot_file,
                                     "Ramp files (*.json)"))

        if path_to_new_file is not '':
            self.path_to_load_mot_file = path_to_new_file


class Overlay(QtGui.QWidget):

    def __init__(self, ramp_editor, scroll_area=None):
        super(Overlay, self).__init__(scroll_area)
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.ramp_editor = ramp_editor
        self.scroll_area = scroll_area

        self.show_overlay = False
        self.bg_color = ramp_editor.palette().color(ramp_editor.backgroundRole())
        self.bg_color.setAlpha(220)
        self.fontPen = QtGui.QPen(QtGui.QColor(0, 0, 0, 255))
        self.brush = QtGui.QBrush(self.bg_color)

    def setShowOverlay(self, show):
        self.show_overlay = show
        self.update()

    def paintEvent(self, event):
        if self.show_overlay:
            time_rects, time_labels = self.ramp_editor.getTimeCellRectangles()
            ch_rects, ch_labels = self.ramp_editor.getChannelCellRectangles()
            x_pos = self.scroll_area.horizontalScrollBar().value()
            y_pos = self.scroll_area.verticalScrollBar().value()
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(self.fontPen)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            move_x = QtCore.QPoint(x_pos, 0)
            move_y = QtCore.QPoint(0, y_pos)
            for r, label in zip(time_rects, time_labels):
                tl, br = r.topLeft(), r.bottomRight()
                r_new = QtCore.QRect(tl-move_x, br-move_x)
                painter.fillRect(r_new, self.brush)
                painter.drawText(r_new, QtCore.Qt.AlignCenter, label)
            for r, label in zip(ch_rects, ch_labels):
                tl, br = r.topLeft(), r.bottomRight()
                r_new = QtCore.QRect(tl-move_y, br-move_y)
                painter.fillRect(r_new, self.brush)
                painter.drawText(r_new, QtCore.Qt.AlignCenter, label)
            painter.end()
