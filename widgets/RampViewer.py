from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import ramps
import brewer2mpl


class RampPlot(pg.PlotWidget):
    """Widget for plotting 1d ramp data."""

    def __init__(self, parent=None, title='Plot1d'):
        super(RampPlot, self).__init__(title=title, parent=parent)

        self.pData = self.plot()  # to plot the data
        self.pData.setPen((255, 255, 255))

    def handleDataChanged(self, x, data):
        self.pData.setData(x=x, y=data)


class MultipleRampPlot(pg.PlotWidget):
    def __init__(self, parent=None, title='Plot1d'):
        super(MultipleRampPlot, self).__init__(title=title, parent=parent)
        color_map = brewer2mpl.get_map('Set2', 'qualitative', 8)
        self.set2 = color_map.mpl_colors

        self.n_plots = 0
        self.plot_dict = {}
        self.addLegend()
        self.setLabel('bottom', 'Time')

    def addPlot(self, plot_name):
        plot = self.plot(name=plot_name)
        plot.setPen(self.n_plots)
        self.n_plots += 1
        self.plot_dict[plot_name] = plot

    def handleDataChanged(self, x, data, plot_name):
        if plot_name not in self.plot_dict:
            self.addPlot(plot_name)
        self.plot_dict[plot_name].setData(x=x, y=data)


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
        self.multiple_ramp_plot = MultipleRampPlot(self, title='View Many Ramps')

        self.addButton = QtGui.QPushButton('Add Plot', self)
        self.addButton.clicked.connect(self.handleAddClicked)

        self.grid.addWidget(self.channel_selector, 0, 0)
        self.grid.addWidget(self.addButton, 0, 1)
        self.grid.addWidget(self.ramp_plot, 1, 0, 2, 2)
        self.grid.addWidget(self.multiple_ramp_plot, 4, 0, 2, 2)
        self.channel_selector.currentIndexChanged.connect(self.handleChannelChanged)

        self.loadSettings()

        self.kfl = ramps.KeyFrameList(self.data_dict['keyframes'])
        self.updatePlot()

    def handleAddClicked(self):
        ci = self.channel_selector.currentIndex()
        ch_name = self.channel_list[ci]
        time, voltage = self.getChannelData(ch_name)
        self.multiple_ramp_plot.handleDataChanged(time, voltage, ch_name)

    def updatePlot(self):
        time, voltage = self.getChannelData(self.current_channel)
        self.ramp_plot.handleDataChanged(time, voltage)

    def getChannelData(self, ch_name):
        ch_dict = self.data_dict['channels'][ch_name]
        channel = ramps.Channel(self.current_channel, ch_dict, self.kfl)
        return channel.generate_ramp()


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
