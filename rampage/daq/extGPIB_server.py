
import inspect
import zmq
import json
import socket

from subprocess import Popen, PIPE
import visa

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


class NewportESP300(RequestProcessor):

    def __init__(self, bind_port):
        self.instr = self.open_instrument()
        RequestProcessor.__init__(self, bind_port)

    def open_instrument(self):
        resource_manager = visa.ResourceManager()
        resource_list = resource_manager.list_resources()
        gpib_address_list = filter(lambda x: x[:4] == 'GPIB', resource_list)

        for addr in gpib_address_list:
            instr = resource_manager.open_resource(addr)
            idn = instr.query('*IDN?')
            if 'ESP300 Version' in idn:
                    return instr

    def set_position(self, mesg):
        axis, pos = mesg['axis'], mesg['position']
        if (not (axis in ['1','2',1,2])):
            return {'success': 0}
        # the min and max correspond to the max and min we know we can move the barrier
        max_pos = -0.035
        min_pos = -0.335
        if (not (type(pos) == float and (pos<=max_pos) and (pos>=min_pos))):
            return {'success': 0}

        self.instr.write(str(axis) + 'PA' + str(np.around(pos, decimals=3)))
        return {'success': 1}

    def read_position(self, mesg):
        num_axes=2
        for i in range(num_axes-1):
            pos = self.instr.query(str(i+1)+'TP?')
            print('Pos' + str(i+1) + ' ' + pos[:8])

        return {'success': 1}

def main():
    esp300 = NewportESP300(5557)
    #esp300._run()


if __name__ == '__main__':
    main()
