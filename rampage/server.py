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
from rampage.zmq_server import RequestProcessor, ClientForServer

# Set this to True if you want to enable DDS functionality
# make sure that the DDS server is running
ENABLE_DDS = False

if __name__ == '__main__':
    # import daq only if server is running
    # not if some other module is importing functions from
    # this module
    from rampage.daq import daq
    from rampage.daq.gpib import agilent_33250a

    if ENABLE_DDS:
        from ramppage.daq import dds_server
        dds_client = ClientForServer(dds_server.DDSCombServer,
                                     'tcp://localhost:5555')

main_package_dir = os.path.dirname(__file__)


class Hooks(object):

    default_mesgs = {'agilent_set_fm_ext': {'freq': 40e6,
                                            'peak_freq_dev':40e6,
                                            'amplitude': 0.7,
                                            'output_state': True},
                     'agilent_set_output': {'state': True},
                     'dds_set_freq': {'freq': 80000000,
                                      'ch': 'A'},
                     'dds_set_amp': {'amp': 1, 'ch': 'A'}
                    }

    def agilent_set_fm_ext(self, mesg_dict):
        agilent_33250a.set_fm_ext(**mesg_dict)
        print('agilent_33250a: set to FM External modulation.')

    def agilent_set_output(self, mesg_dict):
        agilent_33250a.set_output(**mesg_dict)
        print('agilent_33250a: setting output: ' +
              str(mesg_dict['state']))

    def dds_set_freq(self, mesg_dict):
        if ENABLE_DDS:
            print('dds_comb: set_freq: ' +
                  str(mesg_dict))
            dds_client.set_freq(mesg_dict)

    def dds_set_amp(self, mesg_dict):
        if ENABLE_DDS:
            print('dds_comb: set_amp: ' +
                  str(mesg_dict))
            dds_client.set_amp(mesg_dict)


global_hooks_object = Hooks()
global_hooks_object.function_dict = {}
members = inspect.getmembers(global_hooks_object,
                             predicate=inspect.ismethod)
for func_name, func in members:
    global_hooks_object.function_dict[func_name] = func


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


            if self.task_pending and not self.ramp_generated:
                print('Making ramps')
                start_making_time = datetime.datetime.now()
                self.ramp_out = make_ramps(self.current_data)
                end_making_time = datetime.datetime.now()
                dt = end_making_time - start_making_time
                print('Took {0} to make ramps'.format(dt))
                self.ramp_generated = True
                self.task_pending = False

            if self.task_running:
                # check if task is done
                if self.digital_task.is_task_done:
                    self.task_running = False
                    self.task_end_time = datetime.datetime.now()
                    self.waiting_after_running = True
                    self.log_ramps()

                    print('Task ended at {0}'.format(self.task_end_time))
                    dt = self.task_end_time - self.task_start_time
                    print('Task running length {0}'.format(dt))

            elif self.waiting_after_running:
                delta_t = datetime.datetime.now() - self.task_end_time
                time_elapsed_after_task_end = delta_t.total_seconds()*1000
                if time_elapsed_after_task_end > self.wait_time_after_running:
                    print('Waiting time is : ' + str(self.wait_time_after_running))
                    print('Waited for {0} ms\n'.format(time_elapsed_after_task_end))

                    self.waiting_after_running = False


            elif (self.ramp_generated):
                properties = self.prev_data_list[0]['properties']
                if 'wait_after_running' in properties:
                    self.wait_time_after_running = properties['wait_after_running']
                else:
                    self.wait_time_after_running = 0.0
                self.clear_tasks()
                # if not, and if we have a generated ramp, upload it and run

                self.upload_and_start_tasks()

                print('Task started at {0}'.format(self.task_start_time))

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
            self.dev1_task.ClearTask()
            self.dev2_task.ClearTask()
            self.dev3_task.ClearTask()
            self.digital_task.ClearTask()
            # print('Reseting clock to high')
            # daq.reset_analog_sample_clock(False)

    def upload_and_start_tasks(self):
        daq.reset_analog_sample_clock()
        out = self.ramp_out
        dev1_task, dev2_task, dev3_task, digital_task = daq.create_all_tasks(*out)
        dev1_task.StartTask()
        dev2_task.StartTask()
        dev3_task.StartTask()
        digital_task.StartTask()
        self.dev1_task = dev1_task
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
                self.current_data = self.ramps_queue.get(False)
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
    if dev_name == "Dev1":
        n_channels = 4
    else:
        n_channels = 8
    line_fmt = dev_name + "/ao{0:1d}"
    line_ids = [line_fmt.format(n) for n in range(n_channels)]
    return line_ids


def dev1_analog_ids():
    return get_analog_ids("Dev1")


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
        steps_residue = steps_float - round(steps_float)
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
    dev1_trigger_line, dev1_voltages = make_analog_ramps(data, dev_name="Dev1")
    dev2_trigger_line, dev2_voltages = make_analog_ramps(data, dev_name="Dev2")
    dev3_trigger_line, dev3_voltages = make_analog_ramps(data, dev_name="Dev3")
    callback_list = make_callback_list(data)
    return (digital_data, dev1_trigger_line, dev1_voltages,
            dev2_trigger_line, dev2_voltages, dev3_trigger_line,
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
