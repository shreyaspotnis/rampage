from PyQt4 import QtGui, QtCore
from PyQt4 import uic
import sys
import json
import ramps
import os


Ui_RampQueuer, QRampQueuer = uic.loadUiType("ui/RampQueuer.ui")


def flatten_dict(dct, separator='-->', allowed_types=[int, float, bool]):
    flat_list = []
    for key in sorted(dct):
        if key[:2] == '__':
            continue
        key_type = type(dct[key])
        if key_type in allowed_types:
            flat_list.append(str(key))
        elif key_type is dict:
            sub_list = flatten_dict(dct[key])
            sub_list = [str(key) + separator + sl for sl in sub_list]
            flat_list += sub_list

    return flat_list


class RampQueuer(QRampQueuer, Ui_RampQueuer):

    def __init__(self, ramp_dict, settings, parent=None):
        super(RampQueuer, self).__init__(parent)
        self.setupUi(self)
        self.settings = settings
        self.loadSettings()
        self.lineEditPrependRamp.setText(self.path_to_prepend_file)

    def loadSettings(self):
        self.settings.beginGroup('rampqueuer')
        geometry = self.settings.value('geometry').toByteArray()
        self.path_to_prepend_file = str(self.settings.value('path_to_prepend_file',
                                        'examples/test_scene.json').toString())

        check_state, _ = self.settings.value('check_prepend_ramp', 0).toInt()
        print(check_state)
        self.checkPrependRamp.setChecked(bool(check_state))
        self.settings.endGroup()

        self.restoreGeometry(geometry)
        # self.restoreState(state)

    def saveSettings(self):
        self.settings.beginGroup('rampqueuer')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('path_to_prepend_file',
                               self.path_to_prepend_file)
        prepend_ramp_state = int(self.checkPrependRamp.isChecked())
        print('prepend_ramp_state', prepend_ramp_state)
        self.settings.setValue('check_prepend_ramp', prepend_ramp_state)
        self.settings.endGroup()

    def handleChangePrependRamp(self):
        # save old opened file
        func = QtGui.QFileDialog.getOpenFileName
        path_to_new_file = str(func(self, "Open File",
                                    self.path_to_prepend_file,
                                    "Ramp files (*.json)"))

        if path_to_new_file is not '':
            self.path_to_prepend_file = path_to_new_file
            self.lineEditPrependRamp.setText(self.path_to_prepend_file)

    def closeEvent(self, event):
        self.saveSettings()
        super(RampQueuer, self).closeEvent(event)


def main():
    app = QtGui.QApplication(sys.argv)

    main_dir = os.path.dirname(os.path.abspath(__file__))
    print(main_dir)
    main_dir = main_dir + '/../'
    path_to_settings = os.path.join(main_dir, 'settings.ini')
    print(path_to_settings)
    with open(path_to_settings, 'r') as f:
        print(f.read())
    settings = QtCore.QSettings(path_to_settings, QtCore.QSettings.IniFormat)

    with open('examples/test_scene_big.json', 'r') as f:
        data = json.load(f)
    w = RampQueuer(data, settings, None)
    w.show()
    return app.exec_()

if __name__ == '__main__':
    main()
