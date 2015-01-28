#!/usr/bin/env python

import sys
import os
from PyQt4 import QtGui, QtCore
from sys import platform as _platform

from widgets.MainWindow import MainWindow


main_dir = os.path.dirname(os.path.abspath(__file__))
path_to_icon = os.path.join(main_dir, 'icon.png')


def main():
    path_to_settings = os.path.join(main_dir, 'settings.ini')
    settings = QtCore.QSettings(path_to_settings, QtCore.QSettings.IniFormat)
    w = MainWindow(settings)
    w.show()
    return app.exec_()

if __name__ == '__main__':
    print(sys.argv)
    app = QtGui.QApplication(sys.argv)

    if _platform == "win32":
        import ctypes
        myappid = 'steinberglabs.rampage.rampage.0.1'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    print('path', path_to_icon)
    app.setWindowIcon(QtGui.QIcon(path_to_icon))

    main()
    os._exit(0)
