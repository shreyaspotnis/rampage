"""This module handles running the ramps on the experiment."""
import inspect
import zmq
import json
import os
import numpy as np
import threading
import Queue
import datetime
import ConfigParser
import stat

from rampage import ramps

if __name__ == '__main__':
    # import daq only if server is running
    # not if some other module is importing functions from
    # this module
    from rampage.daq import daq

main_package_dir = os.path.dirname(__file__)


class Hooks(object):

    default_mesgs = {'agilent_turn_fm_on': {'start_freq': 40e6},
                     'agilent_output_off': {},
                     'translation_stage_move_x': {'pos': 0.0},
                     'translation_stage_move_y': {'pos': 1.0}
                     }

    def agilent_turn_fm_on(self, mesg_dict):
        # add code to do the gpib stuff
        # print('agilent_turn_fm_on', mesg_dict)
        pass

    def agilent_output_off(self, mesg_dict):
        # print('agilent_output_off', mesg_dict)
        pass

    def translation_stage_move_x(self, mesg_dict):
        # print('translation_stage_move_x', mesg_dict)
        pass

    def translation_stage_move_y(self, mesg_dict):
        # print('translation_stage_move_y', mesg_dict)
        pass


global_hooks_object = Hooks()
global_hooks_object.function_dict = {}
members = inspect.getmembers(global_hooks_object,
                             predicate=inspect.ismethod)
for func_name, func in members:
    global_hooks_object.function_dict[func_name] = func


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
                # print('Message Received:\t' + recv_string)
                request = json.loads(recv_string)
                if request['name'] not in self._messages_dict:
                    reply = {'error': 'Request name not valid.'}
                else:
                    func = self._messages_dict[request['name']]
                    reply = func(request['mesg'])

                send_string = json.dumps(reply)
                # print('Sending:\t' + send_string)
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


class DaqThread(threading.Thread):
    def __init__(self, data_q):
        super(DaqThread, self).__init__()
        self.data_q = data_q
        self.stoprequest = threading.Event()
        self.running = threading.Event()
        self.running.clear()
        self.abort = threading.Event()

        self.digital_task = None

        self.task_running = False
        self.task_pending = False
        self.ramp_generated = False
        self.waiting_after_running = False
        self.current_data = None

        self.prev_data_list = []

        self.main_log_dir = get_log_dir()

    def run(self):
        # As long as we weren't asked to stop, try to take new tasks from the
        # queue. The tasks are taken with a blocking 'get', so no CPU
        # cycles are wasted while waiting.
        # Also, 'get' is given a timeout, so stoprequest is always checked,
        # even if there's nothing in the queue.
        while not self.stoprequest.isSet():
            self.running.wait()
            # print('task_running', self.task_running)
            # print('task_pending', self.task_pending)
            # print('ramp_generated', self.ramp_generated)

            if not self.task_pending:
                try:
                    self.current_data = self.data_q.get(True, 0.05)
                    self.prev_data_list.append(self.current_data)
                except Queue.Empty:
                    pass
                else:
                    print('I Have a new task')
                    # there is data in the queue, which means there is a task
                    # pending to be done
                    self.task_pending = True

                    properties = self.current_data['properties']
                    if 'wait_after_running' in properties:
                        self.wait_time_after_running = properties['wait_after_running']
                    else:
                        self.wait_time_after_running = 0.0

            if self.task_pending and not self.ramp_generated:
                print('Making ramps')
                self.ramp_out = make_ramps(self.current_data)
                self.ramp_generated = True
                self.task_pending = False

            if self.task_running:
                # check if task is done
                if self.digital_task.is_task_done:
                    self.task_running = False
                    self.task_end_time = datetime.datetime.now()
                    self.waiting_after_running = True
                    self.log_ramps()

                    print('Task ended at {0}\n\n'.format(self.task_end_time))
                    dt = self.task_end_time - self.task_start_time
                    print('Task running length {0}'.format(dt))

            elif self.waiting_after_running:
                delta_t = datetime.datetime.now() - self.task_end_time
                time_elapsed_after_task_end = delta_t.total_seconds()*1000
                if time_elapsed_after_task_end > self.wait_time_after_running:
                    print('Waited for {0} ms'.format(time_elapsed_after_task_end))
                    self.waiting_after_running = False
            elif (self.ramp_generated):
                # if not, and if we have a generated ramp, upload it and run
                self.clear_tasks()
                self.upload_and_start_tasks()

                self.task_start_time = datetime.datetime.now()
                print('Task started at {0}\n\n'.format(self.task_start_time))

                self.task_running = True
                self.ramp_generated = False

    def log_ramps(self):
        log_data = self.prev_data_list.pop(0)
        if 'log_ramp_file' in log_data['properties']:
            if not log_data['properties']['log_ramp_file']:
                return

        ls1 = 'Task started at: {0}'.format(self.task_start_time)
        ls2 = 'Task ended at: {0}'.format(self.task_end_time)
        log_string = '\n'.join([ls1, ls2])
        log_data['properties']['run_details'] = log_string
        fname = self.task_start_time.strftime('%H-%M-%S')
        fname += '.json'
        folder_name = make_folder_for_today(self.main_log_dir)
        fname = os.path.join(folder_name, fname)
        with open(fname, 'w') as f:
            json.dump(log_data, f)
        # make the logged file read only
        os.chmod(fname, stat.S_IREAD)

    def clear_tasks(self):
        if self.digital_task is not None:
            self.dev2_task.ClearTask()
            self.dev3_task.ClearTask()
            self.digital_task.ClearTask()

    def upload_and_start_tasks(self):
        daq.reset_analog_sample_clock()
        out = self.ramp_out
        dev2_task, dev3_task, digital_task = daq.create_all_tasks(*out)
        dev2_task.StartTask()
        dev3_task.StartTask()
        digital_task.StartTask()
        self.dev2_task = dev2_task
        self.dev3_task = dev3_task
        self.digital_task = digital_task
        self.task_start_time = datetime.datetime.now()

    def join(self, timeout=None):
        self.stoprequest.set()
        super(DaqThread, self).join(timeout)


class BECServer(RequestProcessor):
    def __init__(self, bind_port):
        RequestProcessor.__init__(self, bind_port)
        self.ramps_queue = Queue.Queue()
        self.daq_thread = DaqThread(self.ramps_queue)
        self.daq_thread.start()

    def start(self, mesg):
        self.daq_thread.running.set()
        reply = {'status': 'ok'}
        return reply

    def pause_after_current_ramp(self, mesg):
        self.daq_thread.running.clear()
        reply = {'status': 'ok'}
        return reply

    def queue_ramp(self, mesg):
        # print('Queueing ramp')
        self.ramps_queue.put(mesg)
        reply = {'status': 'ok'}
        return reply

    def clear_queue(self, mesg):
        print('Clearing ramp')
        # self.ramps_queue = []
        done = False
        while not done:
            try:
                self.current_data = self.data_q.get(False)
            except Queue.Empty:
                done = True
        reply = {'status': 'ok'}
        return reply

    def get_queue_comments(self, mesg):
        # print('Get Queue Comments')
        # comments = [a['properties']['comment'] for a in self.ramps_queue]
        # reply = {'comment_list': comments}
        reply = {'comment_list': ['bla']}
        return reply

    def abort_current_run(self, mesg):
        print(mesg)
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


def make_callback_list(ramp_data):
    keyframe_list = ramps.KeyFrameList(ramp_data['keyframes'])
    callback_list = []
    for hook_item in keyframe_list.get_hooks_list():
        time = hook_item[0]*1e-3  # ramps have time in ms, convert to s
        funcs_list = []
        for func_name, func_dict in hook_item[1]:
            func = global_hooks_object.function_dict[func_name]
            # print('adding func:', func_name, func_dict)
            funcs_list.append((func, func_dict))
        callback_list.append((time, funcs_list))
    return callback_list


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
    callback_list = make_callback_list(data)
    return (digital_data, dev2_trigger_line, dev2_voltages, dev3_trigger_line,
            dev3_voltages, callback_list)


def get_log_dir():
    settings_file = os.path.join(main_package_dir, 'settings.ini')
    config = ConfigParser.RawConfigParser()
    config.read(settings_file)
    log_dir = config.get('server', 'log_dir')
    return log_dir


def make_folder_for_today(log_dir):
    """Creates the folder log_dir/yyyy/mm/dd in log_dir if it doesn't exist
    and returns the full path of the folder."""
    now = datetime.datetime.now()
    sub_folders_list = ['{0:04d}'.format(now.year),
                        '{0:02d}'.format(now.month),
                        '{0:02d}'.format(now.day)]
    folder = log_dir
    for sf in sub_folders_list:
        folder = os.path.join(folder, sf)
        if not os.path.exists(folder):
            os.makedirs(folder)
    return folder


def main():
    s = BECServer(6023)
    s._run()


if __name__ == '__main__':

    main()
