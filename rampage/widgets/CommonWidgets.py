"""Provides useful utility widgets.

Widgets:
    MyDoubleSpinBox(QtGui.QDoubleSpinBox)
    QNamedPushButton(QtGui.QPushButton)
    QMultipleSpinBoxEdit(QtGui.QWidget)
"""

from PyQt4 import QtGui, QtCore


class MyDoubleSpinBox(QtGui.QDoubleSpinBox):

    """Selects all text once it receives a focusInEvent.

    Use this widget instead of the usual QDoubleSpinBox for quick editing.
    """

    def __init__(self, parent):
        super(MyDoubleSpinBox, self).__init__()
        self.setDecimals(3)

    def focusInEvent(self, e):
        super(MyDoubleSpinBox, self).focusInEvent(e)
        QtCore.QTimer.singleShot(100, self.afterFocus)

    def afterFocus(self):
        self.selectAll()


class QNamedPushButton(QtGui.QPushButton):

    """Push button with a name identifier. Use this when multiple push buttons
    are connected to the same slot.

    Signals:
    clicked_name(object) - Emitted whenever user clicks the button. It sends
    its name.
    """

    clicked_name = QtCore.pyqtSignal(object)

    def __init__(self, label, name, parent):
        super(QNamedPushButton, self).__init__(label, parent)
        self.name = name
        self.clicked.connect(self.handleClicked)

    def handleClicked(self):
        self.clicked_name.emit(self.name)


class QMultipleSpinBoxEdit(QtGui.QWidget):

    """Widget to edit a list of floats.

    Signals:

    valueChanged(list) - Emits a list of values whenever any value is changed.
    """

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
            sb.setDecimals(3)
            sb.setMinimum(-10000.)
            sb.setMaximum(10000.)
            sb.setValue(av)
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
