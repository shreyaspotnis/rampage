from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import ramps


class RampPlot(pg.PlotWidget):
    """Widget for plotting 1d ramp data."""

    def __init__(self, parent=None, title='Plot1d'):
        super(RampPlot, self).__init__(title=title, parent=parent)

        self.pData = self.plot()  # to plot the data
        self.pData.setPen((255, 255, 255))

    def handleDataChanged(self, x, data):
        self.pData.setData(x=x, y=data)


class RampViewer(QtGui.QDialog):

    def __init__(self, data_dict, current_channel, settings, parent):
        super(RampViewer, self).__init__()

        self.setWindowTitle('View Ramps')
        self.grid = QtGui.QGridLayout(self)
        self.setLayout(self.grid)
        self.data_dict = data_dict
        self.current_channel = current_channel
        self.settings = settings

        self.channel_list = self.data_dict['channels'].keys()
        self.channel_selector = QtGui.QComboBox(self)
        self.channel_selector.addItems(self.channel_list)
        curr_index = self.channel_list.index(current_channel)
        self.channel_selector.setCurrentIndex(curr_index)
        self.ramp_plot = RampPlot(self, title=current_channel)

        self.grid.addWidget(self.channel_selector, 0, 0)
        self.grid.addWidget(self.ramp_plot, 1, 0, 2, 2)
        self.channel_selector.currentIndexChanged.connect(self.handleChannelChanged)

        self.loadSettings()

        self.kfl = ramps.KeyFrameList(self.data_dict['keyframes'])
        self.updatePlot()

    def updatePlot(self):
        ch_dict = self.data_dict['channels'][self.current_channel]
        channel = ramps.Channel(self.current_channel, ch_dict, self.kfl)
        time, voltage = channel.generate_ramp()
        self.ramp_plot.handleDataChanged(time, voltage)

    def handleChannelChanged(self, new_ch_index):
        self.current_channel = self.channel_list[new_ch_index]
        self.ramp_plot.setTitle(self.current_channel)
        self.updatePlot()

    def loadSettings(self):
        """Load window state from self.settings"""
        self.settings.beginGroup('rampviewer')
        geometry = self.settings.value('geometry').toByteArray()
        self.settings.endGroup()

        self.restoreGeometry(geometry)
        # self.restoreState(state)

    def saveSettings(self):
        """Save window state to self.settings."""
        self.settings.beginGroup('rampviewer')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.endGroup()

    def exec_(self):
        execReturn = super(RampViewer, self).exec_()
        self.saveSettings()
        return execReturn

