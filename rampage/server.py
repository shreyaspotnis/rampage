"""This module handles running the ramps on the experiment."""
import inspect
import zmq
import json
import os
import numpy as np

from rampage import ramps

__usedaq__ = True
if __usedaq__:
    from rampage.daq import daq


main_package_dir = os.path.dirname(__file__)
ui_filename = os.path.join(main_package_dir, "ui/MainWindow.ui")


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
        # find names of all functions in the class
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        self._messages_dict = {}
        for func_name, func in members:
            # ignore hidden functions that start with '_'
            if func_name[0] is not '_':
                self._messages_dict[func_name] = func

        # start a REQ-REP server, zmq stuff
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
        self.digital_task = None

    def start(self, mesg):
        if len(self.ramps_queue) == 0:
            reply = {'status': 'empty queue'}
        else:
            ramp_json_data = self.ramps_queue[0]
            out = make_ramps(ramp_json_data)
            if __usedaq__:
                if self.digital_task is not None:
                    done = self.digital_task.isDone()
                    if not done:
                        reply = {'status': 'previous task still running.'}
                        return reply
                    else:
                        self.dev2_task.ClearTask()
                        self.dev3_task.ClearTask()
                        self.digital_task.ClearTask()
                daq.reset_analog_sample_clock()
                dev2_task, dev3_task, digital_task = daq.create_all_tasks(*out)
                dev2_task.StartTask()
                dev3_task.StartTask()
                digital_task.StartTask()
                self.dev2_task = dev2_task
                self.dev3_task = dev3_task
                self.digital_task = digital_task
            self.ramps_queue.pop(0)
            reply = {'status': 'ok'}

        return reply

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

    def abort_current_run(self, mesg):
        print(mesg)
        reply = {'status': 'ok'}
        return reply

    def pause_after_current_ramp(self, mesg):
        reply = {'status': 'ok'}
        return reply


def digital_channel_ids():
    """Returns list of digital channels used in the experiment."""
    line_fmt = 'Dev1/port0/line{0:02d}'
    line_ids = [line_fmt.format(n) for n in range(8, 31)]
    return line_ids


def get_analog_ids(dev_name="Dev2"):
    line_fmt = dev_name + "/ao{0:1d}"
    line_ids = [line_fmt.format(n) for n in range(8)]
    return line_ids

def dev2_analog_ids():
    return get_analog_ids("Dev2")

def dev3_analog_ids():
    return get_analog_ids("Dev3")


def get_digital_channels(channel_list):
    """Goes through channel list and returns digital channels with ids
    Dev1/port0/line08, Dev1/port0/line09... Dev1/port0/line30."""
    dig_ids = digital_channel_ids()
    dig_channels = []
    for ln in dig_ids:
        for ch in channel_list:
            if ch.dct['id'] == ln:
                dig_channels.append(ch)
                break
    return dig_channels


def get_analog_channels(channel_list, dev_name="Dev2"):
    an_ids = get_analog_ids(dev_name)
    analog_channels = []
    for ln in an_ids:
        for ch in channel_list:
            if ch.dct['id'] == ln:
                analog_channels.append(ch)
                break
    return analog_channels


def make_analog_ramps(ramp_data, dev_name="Dev2"):
    keyframe_list = ramps.KeyFrameList(ramp_data['keyframes'])
    sorted_key_list = keyframe_list.sorted_key_list()
    channel_list = [ramps.Channel(ch_name, ramp_data['channels'][ch_name],
                                  keyframe_list)
                    for ch_name in ramp_data['channels']]

    ramp_properties = ramp_data['properties']
    jump_resolution = ramp_properties['jump_resolution']
    ramp_resolution = ramp_properties['ramp_resolution']
    an_channels = get_analog_channels(channel_list, dev_name)

    ramp_regions = np.zeros(len(sorted_key_list) - 1)
    voltage_array = []
    for an_ch in an_channels:
        ramp_regions += an_ch.get_ramp_regions()
    for an_ch in an_channels:
        time_array, voltages = an_ch.get_analog_ramp_data(ramp_regions,
                                                          jump_resolution,
                                                          ramp_resolution)
        time_array2, voltages2 = an_ch.generate_ramp(jump_resolution)
        # plt.plot(time_array2, voltages2)
        # plt.plot(time_array, voltages, 'o')
        # plt.show()
        voltage_array.append(voltages)
    voltage_array = np.array(voltage_array)
    trigger_line = make_trigger_line(time_array, jump_resolution)
    return trigger_line, voltage_array


def make_trigger_line(time_array, jump_resolution):
    positions = np.rint(time_array/jump_resolution).astype(int)
    print('max position', np.max(positions))
    trigger_line = np.zeros(np.max(positions) + 1, dtype='uint32')
    trigger_line[positions] = True
    return trigger_line


def make_digital_ramps(ramp_data):
    keyframe_list = ramps.KeyFrameList(ramp_data['keyframes'])
    channel_list = [ramps.Channel(ch_name, ramp_data['channels'][ch_name],
                                  keyframe_list)
                    for ch_name in ramp_data['channels']]

    ramp_properties = ramp_data['properties']
    jump_resolution = ramp_properties['jump_resolution']

    # The channels used are Dev1/port0/line8:31
    dig_channels = get_digital_channels(channel_list)

    for line_number, dig_ch in zip(range(8, 31), dig_channels):
        time, ramp_uint = dig_ch.generate_ramp(time_div=jump_resolution)
        if line_number == 8:
            steps = len(ramp_uint)
            digital_data = np.zeros(steps, dtype='uint32')
        digital_data += ramp_uint*(2**line_number)

    return digital_data


def check_ramp_for_errors(ramp_data):
    """Checks ramp for errors. This is experiment specific checklist."""
    error_list = []
    keyframe_list = ramps.KeyFrameList(ramp_data['keyframes'])
    sorted_key_list = keyframe_list.sorted_key_list()
    channel_list = [ramps.Channel(ch_name, ramp_data['channels'][ch_name],
                                  keyframe_list)
                    for ch_name in ramp_data['channels']]
    sorted_absolute_times = [keyframe_list.get_absolute_time(sk) for sk
                             in sorted_key_list]
    ramp_properties = ramp_data['properties']
    jump_resolution = ramp_properties['jump_resolution']
    for key_name, abs_time in zip(sorted_key_list, sorted_absolute_times):
        # check if all times are +ve
        if abs_time < 0.0:
            error_fmt = "keyframe \'{0}\' has negative absolute time {1}"
            error_str = error_fmt.format(key_name, abs_time)
            error_list.append(error_str)

        # check if all times are a multiple of minimum resolution
        steps_float = abs_time / jump_resolution
        steps_residue = steps_float - int(steps_float)
        if steps_residue > 0.0001:
            error_fmt = ("keyframe \'{0}\' has absolute time {1} which is not"
                         " a multiple of jump_resolution {2}")
            error_str = error_fmt.format(key_name, abs_time, jump_resolution)
            error_list.append(error_str)

    # find missing channels
    ch_ids = digital_channel_ids()
    ch_ids += dev2_analog_ids()
    # ignore p31, since we used that for Dev1 timing
    for ch_id in ch_ids:
        n_found = 0
        for ch in channel_list:
            if ch.dct['id'] == ch_id:
                n_found += 1
        if n_found != 1:
            error_fmt = '{0} copies of {1} found. There should only be 1'
            error_str = error_fmt.format(n_found, ch_id)
            error_list.append(error_str)

    return error_list


def make_ramps(data):
    digital_data = make_digital_ramps(data)
    dev2_trigger_line, dev2_voltages = make_analog_ramps(data, dev_name="Dev2")
    dev3_trigger_line, dev3_voltages = make_analog_ramps(data, dev_name="Dev3")

    return (digital_data, dev2_trigger_line, dev2_voltages, dev3_trigger_line,
            dev3_voltages)


def main():
    s = BECServer(6023)
    s._run()


# def test_check_ramp_for_errors():
#     fname = os.path.join(main_package_dir, 'examples/dev2_test.json')
#     with open(fname, 'r') as f:
#         data = json.load(f)
#     check_ramp_for_errors(data)
#     dig_data = make_digital_ramps(data)
#     dev2_trigger_line, dev2_voltages = make_analog_ramps(data, dev_name="Dev2")
#     dev3_trigger_line, dev3_voltages = make_analog_ramps(data, dev_name="Dev3")
#     return dev2_trigger_line, dev2_voltages, dig_data

if __name__ == '__main__':
    # main()
    #main()
    # d2_trig, d2_volt, dig_data = test_check_ramp_for_errors()
    #     fname = os.path.join(main_package_dir, 'examples/dev2_test.json')


    # fname = os.path.join(main_package_dir, 'examples/ramp_does_not_work.json')
    # with open(fname, 'r') as f:
    #     data = json.load(f)
    # ramp_json_data = data
    # out = make_ramps(ramp_json_data)
    # (digital_data, dev2_trigger_line, dev2_voltages, dev3_trigger_line,
    #  dev3_voltages) = out
    # if __usedaq__:
    #     dev2_task, dev3_task, digital_task = daq.create_all_tasks(*out)
    #     dev2_task.StartTask()
    #     dev3_task.StartTask()
    #     digital_task.StartTask()
    #     done = False
    #     while not done:
    #         done = digital_task.isDone()
    #     digital_task.ClearTask()
    main()
