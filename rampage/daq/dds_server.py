"""A server to send commands to the DDS Comb.

Author: Sepehr Ebadi
"""

import inspect
import zmq
import json
import socket

from rampage.zmq_server import RequestProcessor
from rampage.zmq_server import ClientForServer


class DDSCombServer(RequestProcessor):
    def __init__(self, bind_port):
        RequestProcessor.__init__(self, bind_port)
        # write code to connect to DDS comb here
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(('192.168.0.115', 37829))

        
    def set_freq(self, mesg):
        freq, ch = mesg['freq'], mesg['ch']
        if (not (ch in ['A','B','C','D','a','b','c','d'])):
            return {'success': 0}
        if (not (type(freq) == int and (freq<=175000000) and (freq>=30000))):
            return {'success': 0}

        ch = ch.capitalize()

        self.socket.send('F'+ ch + ' ' + str(freq) + ' ')
        return {'success': 1}


    def set_amp(self, mesg):
        amp, ch = mesg['amp'], mesg['ch']

        if (not (ch in ['A','B','C','D','a','b','c','d'])):
            return {'success': 0}
        if (not (type(amp) == int and (amp<=100) and (amp>=0))):
            return {'success': 0}

        ch = ch.capitalize()

        self.socket.send('A'+ ch + ' ' + str(amp) + ' ')
        return {'success': 1}


    def set_phase(self, mesg):
        phase, ch = mesg['phase'], mesg['ch']
        if (not (ch in ['A','B','C','D','a','b','c','d'])):
            return {'success': 0}
        if (not (type(phase) == int and (phase<=359) and (phase>=0))):
            return {'success': 0}

        ch = ch.capitalize()

        self.socket.send('P'+ ch + ' ' + str(phase) + ' ')
        return {'success': 1}


    def sweep_freq(self, mesg):
        low_freq, high_freq, step_size, step_time, ch = \
        mesg['low_freq'], mesg['high_freq'], mesg['step_size'], mesg['step_time'], mesg['ch']

        if (not (ch in ['A','B','C','D','a','b','c','d'])):
            return {'success': 0}
        if (not (type(low_freq) == int and (low_freq<=175000000) and (low_freq>=30000))):
            return {'success': 0}
        if (not (type(high_freq) == int and (high_freq<=175000000) and (high_freq>=30000))):
            return {'success': 0}
        if (high_freq < low_freq):
            return {'success': 0}
        if (not (type(step_size) == int and (step_size<=175000000) and (step_size>=1))):
            return {'success': 0}
        if (not (type(step_time) == int and (step_time<=65000) and (step_time>=4))):
            return {'success': 0}

        ch = ch.capitalize()

        step_time = int(float(step_time)/4) * 4

        self.socket.send('S' + ch + ' ' + str(high_freq) + ' ' + str(low_freq) + ' ' + str(step_size) + ' ' + str(step_time) + ' ')
        return {'success': 1}


    def ramp_amp(self, mesg):
        ramp_time, ch = mesg['ramp_time'], mesg['ch']

        if (not (ch in ['A','B','C','D','a','b','c','d'])):
            return {'success': 0}
        if (not (type(ramp_time) == int and (ramp_time<=255) and (ramp_time>=0))):
            return {'success': 0}

        ch = ch.capitalize()

        self.socket.send('U' + ch + ' ' + str(ramp_time) + ' ')        
        return {'success': 1}


    def reset_phase(self, mesg):
        self.socket.send('R')
        return {'success': 1}


    def version(self, mesg):
        self.socket.send('V')
        return {'success': 1}


    def heartbeat(self, mesg):
        self.socket.send('H')
        reply = self.socket.recv(40)
        return {'reply': reply}


def main():
    s = DDSCombServer(5555)
    s._run()


if __name__ == '__main__':
    main()
