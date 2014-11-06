from PyQt4 import QtGui, QtCore


class MyDoubleSpinBox(QtGui.QDoubleSpinBox):

    """Selects all text once it receives a focusInEvent."""

    def __init__(self, parent):
        super(MyDoubleSpinBox, self).__init__()

    def focusInEvent(self, e):
        super(MyDoubleSpinBox, self).focusInEvent(e)
        QtCore.QTimer.singleShot(100, self.afterFocus)

    def afterFocus(self):
        self.selectAll()


class QMultipleSpinBoxEdit(QtGui.QWidget):

    """Widget to edit a list of floats."""

    valueChanged = QtCore.pyqtSignal(list)

    def __init__(self, attribute_names, parent):
        super(QMultipleSpinBoxEdit, self).__init__(parent)
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)
        self.spin_boxes = []
        for an in attribute_names:
            sb = MyDoubleSpinBox(self)
            sb.setToolTip(an)
            sb.valueChanged.connect(self.handleValueChanged)
            self.vbox.addWidget(sb)
            self.spin_boxes.append(sb)

    def handleValueChanged(self):
        self.valueChanged.emit([sb.value() for sb in self.spin_boxes])

