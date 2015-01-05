"""This module handles running the ramps on the experiment."""
import inspect
import zmq
import json


class Hooks(object):

    default_mesgs = {'agilent_turn_fm_on': {'start_freq': 40e6},
                     'agilent_output_off': {},
                     'translation_stage_move_x': {'pos': 0.0},
                     'translation_stage_move_y': {'pos': 1.0}
                     }

    def agilent_turn_fm_on(self, mesg_dict):
        # add code to do the gpib stuff
        pass

    def agilent_output_off(self, mesg_dict):
        pass

    def translation_stage_move_x(self, mesg_dict):
        pass

    def translation_stage_move_y(self, mesg_dict):
        pass


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


class BECServer(RequestProcessor):
    def __init__(self, bind_port):
        RequestProcessor.__init__(self, bind_port)
        self.ramps_queue = []

    def queue_ramp(self, mesg):
        print('Queueing ramp')
        self.ramps_queue.append(mesg)
        reply = {'status': 'ok'}
        return reply

    def clear_queue(self, mesg):
        print('Clearing ramp')
        self.ramps_queue = []
        reply = {'status': 'ok'}
        return reply

    def get_queue(self, mesg):
        print('Get Queue')
        reply = {'queue_list': self.ramps_queue,
                 'status': 'ok'}
        return reply

    def get_queue_comments(self, mesg):
        print('Get Queue Comments')
        comments = [a['properties']['comment'] for a in self.ramps_queue]
        reply = {'comment_list': comments}
        return reply

    def stop_run(self, mesg):
        print(mesg)
        reply = {'status': 'ok'}
        return reply

    def pause_after_current_ramp(self, mesg):
        reply = {'status': 'ok'}
        return reply


def main():
    s = BECServer(6023)
    s._run()


if __name__ == '__main__':
    main()
