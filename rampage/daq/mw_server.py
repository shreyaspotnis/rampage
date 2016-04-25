"""A server to send commands to Windfreak SynthHD.

    Based on Sepher's code
    Author: Ramon Ramos

"""
import inspect
import zmq
import json
import socket

from subprocess import Popen, PIPE
import serial

class RequestProcessor():
    def __init__(self, bind_port):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        self._messages_dict = {}
        for func_name, func in members:
            if func_name[0] is not '_':
                self._messages_dict[func_name] = func

        bind_addr = 'tcp://*:' + str(bind_port)
        print(bind_addr)
        self._context = zmq.Context(1)
        self._server_sock = self._context.socket(zmq.REP)
        self._server_sock.bind(bind_addr)

    def _run(self):
        done = False
        while not done:
            try:
                recv_string = self._server_sock.recv()
                print('Message Received:\t' + recv_string)
                request = json.loads(recv_string)
                if request['name'] not in self._messages_dict:
                    reply = {'error': 'Request name not valid.'}
                else:
                    func = self._messages_dict[request['name']]
                    reply = func(request['mesg'])

                send_string = json.dumps(reply)
                print('Sending:\t' + send_string)
                self._server_sock.send(send_string)
            except KeyboardInterrupt:
                done = True
                print('Killed using Ctrl C')


class ClientForServer(object):
    def __init__(self, Server, server_endpoint):
        self.server_endpoint = server_endpoint
        members = inspect.getmembers(Server, predicate=inspect.ismethod)
        for func_name, func in members:
            if func_name[0] is not '_':
                self._add_request_name(func_name)

    def _add_request_name(self, req_name):
        def func(mesg):
            request_dict = {'mesg': mesg, 'name': req_name}
            return self._send_request_basic(request_dict, self.server_endpoint)
        func.__name__ = req_name
        setattr(self, func.__name__, func)

    def _send_request_basic(self, request_dict, server_endpoint):
        req_string = json.dumps(request_dict)
        context = zmq.Context(1)
        client = context.socket(zmq.REQ)
        client.connect(server_endpoint)

        client.send(req_string)
        reply = client.recv()

        client.close()
        context.term()
        reply_dict = json.loads(reply)
        return reply_dict


# Later try a way not to hard-code this port
com_port = 'COM3'

class SynthHDSerial(RequestProcessor):
    def __init__(self, bind_port):
        self.serv = serial.Serial(com_port, 38400, timeout=0, parity = serial.PARITY_EVEN)
        RequestProcessor.__init__(self, bind_port)

    def mw_set_freq(self, mesg):
        freq, ch = mesg['freq'], mesg['ch']
        if (not (ch in ['0','1',0,1])):
            return {'success': 0}
        if (not (type(freq) == float and (freq<=13000.0) and (freq>=100.0))):
            return {'success': 0}

        self.serv.write('C'+ str(ch) + 'f' + str(freq))
        return {'success': 1}


    def set_amp(self, mesg):
        amp, ch = mesg['amp'], mesg['ch']
        if (not (ch in ['0','1',0,1])):
            return {'success': 0}
        if (not (type(amp) == int and (amp<=45000) and (amp>=0))):
            return {'success': 0}

        self.serv.write('C'+ str(ch) + 'a' + str(amp))
        return {'success': 1}


    def set_phase(self, mesg):
        phase, ch = mesg['phase'], mesg['ch']
        if (not (ch in ['0','1',0,1])):
            return {'success': 0}
        if (not (type(phase) == int and (phase<=359) and (phase>=0))):
            return {'success': 0}

        self.serv.write('C'+ str(ch) + '~' + str(phase))
        return {'success': 1}


    def help(self):
        str_send = '?'
        self.serv.write(str_send)
        reply = self.serv.read(2000)
        return reply

def main():
    mw = SynthHDSerial(5556)
    mw._run()


if __name__ == '__main__':
    main()
