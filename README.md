# rampage

rampage is an arbitrary waveform builder and a control system for ultra-cold
atom and ion trap experiments.  It is written in python and is primarily GUI
based, with modules available to edit and run ramps over the command line.
It follows a client-server architecture: the server is
a command line program running on the control PC and the client communicates
with the server via TCP/IP using zeromq. This allows the experiment to be
controlled from anywhere within the local network.

rampage consists of four parts:
- Implementation of a JSON based ramp description format
- A PyQt4 based GUI to edit the ramp description
- A server that converts a ramp description into analog and digital waveforms,
uploads these on National Instruments DAQ cards, and controls the experiment.
- A ramp queuer for batch running.

## Requirements
rampage is written in PyQt4 and uses pyqtgraph for plotting. Hence, it is
completely cross-platform. It has been tested on Windows, Mac and Linux using
python 2.7. The following python packages are required:

- [PyQt4](https://www.riverbankcomputing.com/software/pyqt/download)
- [pyqtpgraph](http://www.pyqtgraph.org/)
- [numpy](http://www.numpy.org/)
- [zeromq](http://zeromq.org/)

Except for PyQt4, all packages can be installed using pip:

```bash
pip install pyqtgraph
pip install numpy
pip install pyzmq
```

pip does not install PyQt4 correctly. Get the wheel package from [here](http://www.lfd.uci.edu/~gohlke/pythonlibs/) and install it.


## Installation

```bash
pip install rampage
```

If you wish to modify the code, download the package in a local directory
and install it in develop mode.

```bash
cd path/to/installation
git clone https://github.com/shreyaspotnis/rampage
cd rampage
python setup.py develop
```

## Running

```bash
python -m rampage

```



