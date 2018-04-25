"""Create queues of ramps to upload to server.
"""
from PyQt4 import QtGui, QtCore
from PyQt4 import uic
import sys
import json
import os
import numpy as np
from sys import platform as _platform


main_dir = os.path.dirname(os.path.abspath(__file__))
path_to_icon = os.path.join(main_dir, 'queuer_icon.png')


from rampage import server


# utility functions
def run_ramp_immediately(path_to_ramp_file, settings=None):
    with open(path_to_ramp_file, 'r') as f:
        data = json.load(f)
    settings.beginGroup('rampqueuer')
    text = settings.value('server_ip_and_port',
                          'tcp://localhost:6023').toString()
    settings.endGroup()
    client = server.ClientForServer(server.BECServer, str(text))
    # since we are just testing it out, do not wait for the extra time
    data['properties']['wait_after_running'] = 0.
    client.queue_ramp(data)
    client.start({})


def queue_ramp_pair(path_to_ramp_file1, path_to_ramp_file2, settings=None):
    with open(path_to_ramp_file1, 'r') as f:
        data1 = json.load(f)
    with open(path_to_ramp_file2, 'r') as f:
        data2 = json.load(f)
    settings.beginGroup('rampqueuer')
    text = settings.value('server_ip_and_port',
                          'tcp://localhost:6023').toString()
    settings.endGroup()
    client = server.ClientForServer(server.BECServer, str(text))
    client.queue_ramp(data1)
    client.queue_ramp(data2)
    client.start({})

def queue_ramp_dicts(ramp_dict_list, server_ip_and_port):
    """Simple utility function to queue up a list of dictionaries."""
    client = server.ClientForServer(server.BECServer, server_ip_and_port)
    for dct in ramp_dict_list:
        client.queue_ramp(dct)
    client.start({})



def flatten_dict(dct, separator='-->', allowed_types=[int, float, bool]):
    """Returns a list of string identifiers for each element in dct.

    Recursively scans through dct and finds every element whose type is in
    allowed_types and adds a string indentifier for it.

    eg:
    dct = {
            'a': 'a string',
            'b': {
                'c': 1.0,
                'd': True
            }
          }
    flatten_dict(dct) would return
    ['a', 'b-->c', 'b-->d']
    """
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


def set_dict_item(dct, name_string, set_to):
    """Sets dictionary item identified by name_string to set_to.

    name_string is the indentifier generated using flatten_dict.

    Maintains the type of the orginal object in dct and tries to convert set_to
    to that type.
    """
    key_strings = str(name_string).split('-->')
    d = dct
    for ks in key_strings[:-1]:
        d = d[ks]
    item_type = type(d[key_strings[-1]])
    d[key_strings[-1]] = item_type(set_to)

main_package_dir = os.path.dirname(__file__)
ui_filename = os.path.join(main_package_dir, "ui/Ramp1DScan.ui")
Ui_Ramp1DScan, QRamp1DScan = uic.loadUiType(ui_filename)


class Ramp1DScan(QRamp1DScan, Ui_Ramp1DScan):

    def __init__(self, column_names_list, parent=None):
        super(Ramp1DScan, self).__init__(parent)
        self.setupUi(self)
        self.num_scan_cols = 0
        self.scan_columns = []
        self.column_names_list = column_names_list
        self.addScanColumn()
        self.spinNumPoints.setValue(1)
        self.spinNumRep.setValue(1)

    def handleNumPointsChanged(self, new_num_points):
        print(new_num_points)
        self.tableScanPoints.setRowCount(new_num_points)

    def handleNumRepsChanged(self, new_num_reps):
        print(new_num_reps)
        self.NumReps = new_num_reps

    def handleAddClicked(self):
        self.addScanColumn()

    def addScanColumn(self):
        start_index = 5
        grid_row_number = start_index + self.num_scan_cols + 1
        self.num_scan_cols += 1

        combo = QtGui.QComboBox(self)
        combo.addItems(self.column_names_list)

        start_label = QtGui.QLabel('Start:')
        start_val = QtGui.QDoubleSpinBox(self)
        start_val.setMinimum(-1e100)
        start_val.setMaximum(1e100)
        start_val.setDecimals(7)

        step_label = QtGui.QLabel('Step:')
        step_val = QtGui.QDoubleSpinBox(self)
        step_val.setMinimum(-1e100)
        step_val.setMaximum(1e100)
        step_val.setDecimals(7)

        for i, widget in enumerate((combo, start_label, start_val,
                                    step_label, step_val)):
            self.gridLayout.addWidget(widget, grid_row_number, i)
        self.scan_columns.append((combo, start_val, step_val))
        self.tableScanPoints.setColumnCount(self.num_scan_cols)

    def handleProgramValues(self):
        for col in range(self.num_scan_cols):
            scan_col = self.scan_columns[col]
            col_name = str(scan_col[0].currentText())
            start_val = float(scan_col[1].value())
            step_val = float(scan_col[2].value())

            vals = np.arange(self.spinNumPoints.value())*step_val + start_val
            for i, v in enumerate(vals):
                item = QtGui.QTableWidgetItem(str(v))
                self.tableScanPoints.setItem(i, col, item)

            print(col_name, start_val, step_val)

    def getTableArray(self):
        num_cols = self.tableScanPoints.columnCount()
        num_rows = self.tableScanPoints.rowCount()
        vals = [[float(self.tableScanPoints.item(nr, nc).text())
                 for nc in range(num_cols)]
                for nr in range(num_rows)]
        return np.array(vals)

    def setTableArray(self, arr):
        num_cols = arr.shape[1]
        self.tableScanPoints.setColumnCount(num_cols)
        num_rows = arr.shape[0]
        self.tableScanPoints.setRowCount(num_rows)
        # for i in range(num_cols-1):
        #     self.addScanColumn()
        print num_cols, num_rows
        for nr in range(num_rows):
            for nc in range(num_cols):
                item = QtGui.QTableWidgetItem(str(arr[nr, nc]))
                print item
                self.tableScanPoints.setItem(nr, nc, item)

    def handleRandomizeClicked(self):
        print('randomize')
        vals = self.getTableArray()
        np.random.shuffle(vals)
        self.setTableArray(vals)

    def handleSaveClicked(self):
        vals = self.getTableArray()
        fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Save file', '.'))
        if fname != '':
            np.savetxt(fname, vals)

    def handleLoadClicked(self):
        print('load')
        fname = str(QtGui.QFileDialog.getOpenFileName(self, "Open File"))
        if fname != '':
            vals = np.loadtxt(fname)
            if len(vals.shape) == 1:
                nrows, ncols = vals.shape[0], 1
            else:
                nrows, ncols = vals.shape
            print nrows, ncols
            self.spinNumPoints.setValue(nrows)
            self.setTableArray(vals.reshape([nrows, ncols]))

    def exec_(self):
        execReturn = super(Ramp1DScan, self).exec_()
        if execReturn:
            num_cols = self.num_scan_cols
            num_rows = self.tableScanPoints.rowCount()
            vals = self.getTableArray()
            col_names = [str(self.scan_columns[i][0].currentText())
                         for i in range(num_cols)]
            reps = self.NumReps
        else:
            col_names = []
            vals = np.array([])
            reps = 1
        return execReturn, col_names, vals, reps

ui_filename = os.path.join(main_package_dir, "ui/Ramp2DScan.ui")
Ui_Ramp2DScan, QRamp2DScan = uic.loadUiType(ui_filename)


class Ramp2DScan(QRamp2DScan, Ui_Ramp2DScan):

    def __init__(self, column_names_list, parent=None):
        super(Ramp2DScan, self).__init__(parent)
        self.setupUi(self)
        self.num_scan_cols = 0
        self.scan_columns = []
        self.column_names_list = column_names_list
        self.addScanColumn()
        self.addScanColumn()
        self.spinNumPoints1.setValue(1)
        self.spinNumPoints2.setValue(1)
        self.spinNumRep.setValue(1)

    def handleNumRepsChanged(self, new_num_reps):
        print(new_num_reps)
        self.NumReps = new_num_reps

    def addScanColumn(self):
        start_index = 5
        grid_row_number = start_index + self.num_scan_cols + 1
        self.num_scan_cols += 1

        combo = QtGui.QComboBox(self)
        combo.addItems(self.column_names_list)

        start_label = QtGui.QLabel('Start:')
        start_val = QtGui.QDoubleSpinBox(self)
        start_val.setMinimum(-1e100)
        start_val.setMaximum(1e100)
        start_val.setDecimals(7)

        step_label = QtGui.QLabel('Step:')
        step_val = QtGui.QDoubleSpinBox(self)
        step_val.setMinimum(-1e100)
        step_val.setMaximum(1e100)
        step_val.setDecimals(7)

        for i, widget in enumerate((combo, start_label, start_val,
                                    step_label, step_val)):
            self.gridLayout.addWidget(widget, grid_row_number, i)
        self.scan_columns.append((combo, start_val, step_val))
        self.tableScanPoints.setColumnCount(self.num_scan_cols)

    def handleProgramValues(self):
        self.tableScanPoints.setRowCount(self.spinNumPoints1.value()*self.spinNumPoints2.value())
        scan_col = self.scan_columns[0]
        col_name = str(scan_col[0].currentText())
        start_val = float(scan_col[1].value())
        step_val = float(scan_col[2].value())
        vals1 = np.arange(self.spinNumPoints1.value())*step_val + start_val

        scan_col = self.scan_columns[1]
        col_name = str(scan_col[0].currentText())
        start_val = float(scan_col[1].value())
        step_val = float(scan_col[2].value())
        vals2 = np.arange(self.spinNumPoints2.value())*step_val + start_val

        tot_vals = np.array([[i, j] for i in vals1 for j in vals2])

        for col in range(self.num_scan_cols):
            for i, v in enumerate(tot_vals[:,col]):
                item = QtGui.QTableWidgetItem(str(v))
                self.tableScanPoints.setItem(i, col, item)

    def getTableArray(self):
        num_cols = self.tableScanPoints.columnCount()
        num_rows = self.tableScanPoints.rowCount()
        vals = [[float(self.tableScanPoints.item(nr, nc).text())
                 for nc in range(num_cols)]
                for nr in range(num_rows)]
        return np.array(vals)

    def setTableArray(self, arr):
        num_cols = arr.shape[1]
        self.tableScanPoints.setColumnCount(num_cols)
        num_rows = arr.shape[0]
        self.tableScanPoints.setRowCount(num_rows)
        print num_cols, num_rows
        for nr in range(num_rows):
            for nc in range(num_cols):
                item = QtGui.QTableWidgetItem(str(arr[nr, nc]))
                print item
                self.tableScanPoints.setItem(nr, nc, item)

    def handleRandomizeClicked(self):
        print('randomize')
        vals = self.getTableArray()
        np.random.shuffle(vals)
        self.setTableArray(vals)

    def handleSaveClicked(self):
        vals = self.getTableArray()
        fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Save file', '.'))
        if fname != '':
            np.savetxt(fname, vals)

    def exec_(self):
        execReturn = super(Ramp2DScan, self).exec_()
        if execReturn:
            num_cols = self.num_scan_cols
            num_rows = self.tableScanPoints.rowCount()
            vals = self.getTableArray()
            col_names = [str(self.scan_columns[i][0].currentText())
                         for i in range(num_cols)]
            reps = self.NumReps
        else:
            col_names = []
            vals = np.array([])
            reps = 1
        return execReturn, col_names, vals, reps


main_package_dir = os.path.dirname(__file__)
ui_filename = os.path.join(main_package_dir, "ui/RampQueuer.ui")
Ui_RampQueuer, QRampQueuer = uic.loadUiType(ui_filename)


class RampQueuer(QRampQueuer, Ui_RampQueuer):

    def __init__(self, settings, parent=None):
        super(RampQueuer, self).__init__(parent)
        self.setupUi(self)
        self.settings = settings
        self.loadSettings()
        self.lineEditPrependRamp.setText(self.path_to_prepend_file)
        self.lineEditMainRamp.setText(self.path_to_main_file)
        self.ramps_to_queue = []
        print(self.serverIPAndPort.text())

    def get_client(self):
        return server.ClientForServer(server.BECServer,
                                      str(self.serverIPAndPort.text()))

    def loadSettings(self):
        self.settings.beginGroup('rampqueuer')
        geometry = self.settings.value('geometry').toByteArray()
        self.path_to_prepend_file = str(self.settings.value('path_to_prepend_file',
                                        'examples/test_scene.json').toString())
        self.path_to_main_file = str(self.settings.value('path_to_main_file',
                                     'examples/test_scene.json').toString())

        check_state, _ = self.settings.value('check_prepend_ramp', 0).toInt()
        text = self.settings.value('server_ip_and_port', 'tcp://localhost:6023').toString()
        self.serverIPAndPort.setText(text)
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
        self.settings.setValue('path_to_main_file',
                               self.path_to_main_file)
        prepend_ramp_state = int(self.checkPrependRamp.isChecked())
        print('prepend_ramp_state', prepend_ramp_state)
        self.settings.setValue('check_prepend_ramp', prepend_ramp_state)
        self.settings.setValue('server_ip_and_port',
                               self.serverIPAndPort.text())
        self.settings.endGroup()

    def handleChangePrependRamp(self):
        func = QtGui.QFileDialog.getOpenFileName
        path_to_new_file = str(func(self, "Open File",
                                    self.path_to_prepend_file,
                                    "Ramp files (*.json)"))

        if path_to_new_file is not '':
            self.path_to_prepend_file = path_to_new_file
            self.lineEditPrependRamp.setText(self.path_to_prepend_file)

    def handleChangeMainRamp(self):
        func = QtGui.QFileDialog.getOpenFileName
        path_to_new_file = str(func(self, "Open File",
                                    self.path_to_main_file,
                                    "Ramp files (*.json)"))

        if path_to_new_file is not '':
            self.path_to_main_file = path_to_new_file
            self.lineEditMainRamp.setText(self.path_to_main_file)

    def handleAddCurrent(self):
        n_add = self.spinNumberReps.value()
        ramp_dict = self.getMainRampDict()
        for ni in range(n_add):
            self.addRamp(ramp_dict)

    def addRamp(self, ramp_dict):
        if self.checkPrependRamp.isChecked():
            print('is checked')
            prepend_data = self.getPrependRampDict()
            self.ramps_to_queue.append(prepend_data)
            self.listToQueue.addItem(prepend_data['properties']['comment'])
        self.ramps_to_queue.append(ramp_dict)
        self.listToQueue.addItem(ramp_dict['properties']['comment'])

    def add1dScanRamps(self, col_names, vals, reps):
        n_rows, n_cols = vals.shape
        for j in range(reps):
            for nr in range(n_rows):
                val_data = vals[nr, :]
                new_ramp_dict = self.getMainRampDict()
                comment_string = []
                for i, cn in enumerate(col_names):
                    set_dict_item(new_ramp_dict, cn, val_data[i])
                    comment_string.append(str(cn) + '=' + str(val_data[i]))
                comment_string = ', '.join(comment_string)
                new_ramp_dict['properties']['comment'] += 'Scan:' + comment_string
                self.addRamp(new_ramp_dict)

    def handle1DScanPressed(self):
        column_names_list = flatten_dict(self.getMainRampDict())
        ramp_1d_scan_generator = Ramp1DScan(column_names_list, self)
        exec_return, col_names, vals, reps = ramp_1d_scan_generator.exec_()
        if exec_return:
            self.add1dScanRamps(col_names, vals, reps)
        print(exec_return)

    def handle2DScanPressed(self):
        column_names_list = flatten_dict(self.getMainRampDict())
        ramp_2d_scan_generator = Ramp2DScan(column_names_list, self)
        exec_return, col_names, vals, reps = ramp_2d_scan_generator.exec_()
        if exec_return:
            self.add1dScanRamps(col_names, vals, reps)
        print(exec_return)

    def closeEvent(self, event):
        self.saveSettings()
        super(RampQueuer, self).closeEvent(event)

    def handleQueueToServerPressed(self):
        for ramp in self.ramps_to_queue:
            self.textServerMesg.append('Queueing')
            reply = self.get_client().queue_ramp(ramp)
            self.textServerMesg.append(str(reply))

        self.ramps_to_queue = []
        self.listToQueue.clear()
        self.handleUpdateServerQueuePressed()

    def handleUpdateServerQueuePressed(self):
        self.listQueued.clear()
        self.textServerMesg.append('Getting Queue on Server')
        reply = self.get_client().get_queue_comments({})
        self.listQueued.addItems(reply['comment_list'])
        num_queued = len(reply['comment_list'])
        self.textServerMesg.append('# of queued ramps: '+str(num_queued))

    def handlePauseAfterCurrent(self):
        print('pasue after current')
        reply = self.get_client().pause_after_current_ramp({})
        self.textServerMesg.append('Pausing after current run.')
        self.textServerMesg.append('Reply: '+str(reply))

    def handleClearServerQueue(self):
        print('cleaning server queue')
        reply = self.get_client().clear_queue({})
        self.textServerMesg.append('Clearing queue')
        self.textServerMesg.append('Reply: '+str(reply))
        self.handleUpdateServerQueuePressed()

    def handleClearLocalQueue(self):
        print('clearing local queue')
        self.ramps_to_queue = []
        self.listToQueue.clear()

    def handleAbortCurrentRun(self):
        print('abort current run')
        reply = self.get_client().abort_current_run({})
        self.textServerMesg.append('Aborting current run')
        self.textServerMesg.append('Reply: '+str(reply))

    def handlePushStart(self):
        print('starting BEC')
        reply = self.get_client().start({})
        self.textServerMesg.append('Starting ramps')
        self.textServerMesg.append('Reply: '+str(reply))

    def getMainRampDict(self):
        with open(self.path_to_main_file, 'r') as f:
            ramp_dict = json.load(f)
        return ramp_dict

    def getPrependRampDict(self):
        with open(self.path_to_prepend_file, 'r') as f:
            ramp_dict = json.load(f)
        return ramp_dict


def main():
    app = QtGui.QApplication(sys.argv)

    main_dir = os.path.dirname(os.path.abspath(__file__))

    if os.access(main_dir, os.W_OK):
        # if yes, then put all settings in an ini file there
        path_to_settings = os.path.join(main_dir, 'settings.ini')
        settings = QtCore.QSettings(path_to_settings,
                                    QtCore.QSettings.IniFormat)
    else:
        # else use Qt settings system
        settings = QtCore.QSettings('rampage', 'Shreyas Potnis')

    if _platform == "win32":
        import ctypes
        myappid = 'steinberglabs.rampage.queuer.0.1'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    print('path', path_to_icon)
    app.setWindowIcon(QtGui.QIcon(path_to_icon))

    w = RampQueuer(settings, None)
    w.show()
    return app.exec_()

if __name__ == '__main__':
    main()
