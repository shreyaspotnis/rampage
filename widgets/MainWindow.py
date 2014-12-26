from PyQt4 import uic
from PyQt4.QtGui import QFileDialog
from PyQt4 import QtGui, QtCore
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

        # self.overlay = Overlay(self.centralWidget())
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

    def handleToggleOverlay(self):
        self.show_overlay = not self.show_overlay
        self.overlay.setShowOverlay(self.show_overlay)

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
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
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
