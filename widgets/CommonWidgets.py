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

    def __init__(self, attribute_names, parent, attribute_values=None):
        super(QMultipleSpinBoxEdit, self).__init__(parent)
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)
        self.attribute_names = attribute_names
        if attribute_values is None:
            self.attribute_values = [0.0]*len(self.attribute_names)
        else:
            self.attribute_values = attribute_values
        self.makeSpinBoxes()

    def makeSpinBoxes(self):
        self.spin_boxes = []
        for an, av in zip(self.attribute_names, self.attribute_values):
            sb = MyDoubleSpinBox(self)
            sb.setToolTip(an)
            sb.setValue(av)
            sb.setDecimals(3)
            sb.setMinimum(-100.)
            sb.setMaximum(100.)
            sb.valueChanged.connect(self.handleValueChanged)
            self.vbox.addWidget(sb)
            self.spin_boxes.append(sb)

    def handleValueChanged(self):
        self.valueChanged.emit([sb.value() for sb in self.spin_boxes])

    def editAttributes(self, new_attribute_names, new_attribute_values=None):
        for sb in self.spin_boxes:
            self.vbox.removeWidget(sb)
            sb.valueChanged.disconnect(self.handleValueChanged)
            sb.deleteLater()
        self.spin_boxes = []
        self.attribute_names = new_attribute_names
        if new_attribute_values is None:
            self.attribute_values = [0.0]*len(self.attribute_names)
        else:
            self.attribute_values = new_attribute_values
        self.makeSpinBoxes()



