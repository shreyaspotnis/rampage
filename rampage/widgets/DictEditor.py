from PyQt4 import QtGui, QtCore
import sys
from collections import namedtuple


class BoolBox(QtGui.QPushButton):
    myValueChanged = QtCore.pyqtSignal(bool)

    def __init__(self, value, parent=None):
        super(BoolBox, self).__init__(parent)
        self.setCheckable(True)
        self.state = value
        self.setChecked(self.state)
        if self.state:
            text = 'ON'
        else:
            text = 'OFF'
        self.setText(text)
        self.clicked.connect(self.handleBoolButtonClicked)
        stylesheet = ('QPushButton:checked { background-color:'
                      'rgb(100,255,125); }'
                      'QPushButton { background-color:'
                      'rgb(255,125,100); }')
        self.setStyleSheet(stylesheet)

    def handleBoolButtonClicked(self, checked):
        self.state = bool(checked)
        if self.state:
            text = 'ON'
        else:
            text = 'OFF'
        self.setText(text)
        self.myValueChanged.emit(self.state)

    def mySetValue(self, val):
        self.state = bool(val)
        self.setChecked(self.state)
        if self.state:
            text = 'ON'
        else:
            text = 'OFF'
        self.setText(text)


class IntBox(QtGui.QSpinBox):
    myValueChanged = QtCore.pyqtSignal(int)

    def __init__(self, value, parent=None):
        super(IntBox, self).__init__(parent)
        self.setValue(value)
        self.setRange(-2000000000, 2000000000)
        self.valueChanged.connect(self.myValueChanged)

    def mySetValue(self, val):
        self.setValue(val)


class FloatBox(QtGui.QDoubleSpinBox):
    myValueChanged = QtCore.pyqtSignal(float)

    def __init__(self, value, parent=None):
        super(FloatBox, self).__init__(parent)
        self.setRange(-1e100, 1e100)
        self.setValue(value)
        self.setDecimals(10)
        self.valueChanged.connect(self.myValueChanged)

    def mySetValue(self, val):
        self.setValue(val)


class StringBox(QtGui.QPlainTextEdit):

    myValueChanged = QtCore.pyqtSignal(str)

    def __init__(self, value, parent=None):
        super(StringBox, self).__init__(parent)
        # self.setPlainText(value)
        self.mySetValue(value)
        self.textChanged.connect(self.handleTextChanged)

    def mySetValue(self, val):
        self.setPlainText(val)

    def handleTextChanged(self):
        self.myValueChanged.emit(str(self.toPlainText()))


# class DropDownBox(QtGui.QComboBox):

#     myValueChanged = QtCore.pyqtSignal(str)

#     def __init__(self, dropdownselection, parent=None):
#         super(DropDownBox, self).__init__(parent)
#         self.dropdownselection = dropdownselection
#         self.addItems(dropdownselection[1])
#         self.setCurrentIndex(dropdownselection[0])

#         self.currentIndexChanged.connect(self.handleIndexChanged)

#     def handleIndexChanged(self, new_value):
#         self.dropdownselection = DropDownSelection(new_value,
#                                                    self.dropdownselection[1])

#     def mySetValue(self, val):
#         self.dropdownselection = val
#         self.setCurrentIndex(self.dropdownselection[0])


# DropDownSelection = namedtuple('DropDownSelection', ['value', 'list_of_options'], verbose=True)


class ListBox(QtGui.QPlainTextEdit):

    myValueChanged = QtCore.pyqtSignal(list)

    def __init__(self, value, parent=None):
        super(ListBox, self).__init__(parent)
        self.mySetValue(value)
        self.textChanged.connect(self.handleTextChanged)

    def mySetValue(self, val):
        self.setPlainText(repr(val))

    def handleTextChanged(self):
        try:
            new_list = eval(str(self.toPlainText()), {}, {})
        except:
            print "Unexpected error:", sys.exc_info()[0]
        else:
            self.myValueChanged.emit(new_list)


widgets_for_type = {int: IntBox, float: FloatBox, str: StringBox,
                    list: ListBox, unicode: StringBox, bool: BoolBox}


class NamedEditor(QtGui.QWidget):

    valueChaged = QtCore.pyqtSignal(str, object)  # key_name, new_value

    def __init__(self, name, value, grid, row, parent=None):
        super(NamedEditor, self).__init__(parent)
        name_label = QtGui.QLabel(name, self)

        key_type = type(value)
        sub_widget = widgets_for_type[key_type](value)
        sub_widget.mySetValue(value)
        sub_widget.myValueChanged.connect(self.handleValueChanged)

        grid.addWidget(name_label, row, 0)
        grid.addWidget(sub_widget, row, 1)

        self.name = name

    def handleValueChanged(self, new_value):
        self.valueChaged.emit(self.name, new_value)


class DictEditor(QtGui.QDialog):

    def __init__(self, dct, dct_name=None, parent=None):
        super(DictEditor, self).__init__(parent)

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        self.dct = dct

        self.button_ok = QtGui.QPushButton('Ok', self)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel = QtGui.QPushButton('Cancel', self)
        self.button_cancel.clicked.connect(self.reject)
        for i, (key, value) in enumerate(sorted(dct.items())):
            key_type = type(value)
            print key_type
            if key_type in widgets_for_type:
                print('i am in')
                named_widget = NamedEditor(key, value, grid, i, self)
                named_widget.valueChaged.connect(self.handleValueChanged)
                grid.addWidget(named_widget, i, 0)
        i = len(dct)
        grid.addWidget(self.button_cancel, i, 0)
        grid.addWidget(self.button_ok, i, 1)

        if dct_name is not None:
            self.setWindowTitle(dct_name)

    def handleValueChanged(self, key_name, new_value):
        if type(new_value) is QtCore.QString:
            new_value = str(new_value)
        self.dct[str(key_name)] = new_value


def main():
    app = QtGui.QApplication(sys.argv)
    dct = {}
    dct['name'] = "a string"
    dct['float_val'] = 1.0
    dct['int_val'] = 5
    dct['bool'] = True
    dct['list_stuff'] = [0.0, "string", True, 1]
    edit_dct = dict(dct)
    d = DictEditor(edit_dct)
    print(d.exec_())
    print dct
    print edit_dct
    return

if __name__ == '__main__':
    main()
