"""This module handles running the ramps on the experiment."""
import inspect
import json
import os
import numpy as np
import threading
import Queue
import datetime
import ConfigParser
import stat
import time
import logging
import logging.handlers
import zmq

from rampage import ramps
from rampage.zmq_server import RequestProcessor, ClientForServer
#from rampage.widgets.DictEditor import DropDownSelection

if __name__ == '__main__':

    format_string = '[%(asctime)s][%(levelname)s] %(message)s'
    logging.basicConfig(format=format_string,
                        level=logging.INFO)

    handler = logging.handlers.RotatingFileHandler('E:\\rampage.server.logs\\server.log',
                                                   maxBytes=1024*1024,
                                                   backupCount=10)
    handler.setFormatter(logging.Formatter(format_string))
    logging.getLogger().addHandler(handler)
    # logging.getLogger().addHandler(logging.StreamHandler())

    # Set this to True if you want to enable DDS functionality
    # make sure that the DDS server is running
    ENABLE_DDS = True

    # Set this to True if you want to enable SynthHD (MW) functionality
    # make sure that MW server is running
    ENABLE_MW = True

    # Set this to True if you want to enable external GPIB functionality
    # make sure that external GPIB server is running
    ENABLE_extGPIB = True

    # import daq only if server is running
    # not if some other module is importing functions from
    # this module
    from rampage.daq import daq
    from rampage.daq.gpib import agilent_33250a, rigolDG1022Z , stanfordSG384, tektronixTDS1002#,  agilentN900A#, newportesp300, tektronixTDS2012C
    zmq_context = zmq.Context()
    pub_socket = zmq_context.socket(zmq.PUB)
    pub_socket.bind('tcp://*:8081')
    if ENABLE_DDS:
        from rampage.daq import dds_server
        dds_client = ClientForServer(dds_server.DDSCombServer,
                                     'tcp://192.168.0.108:5555')

    if ENABLE_MW:
        from rampage.daq import mw_server
        # mw_client = ClientForServer(mw_server.SynthHDSerial,
        #                              'tcp://192.168.0.110:5556')
        mw_client = ClientForServer(mw_server.SynthHDSerial,
                                     'tcp://localhost:5556')

    if ENABLE_extGPIB:
        from rampage.daq import extGPIB_server
        extGPIB_client = ClientForServer(extGPIB_server.NewportESP300,
                                     'tcp://192.168.0.116:5561')

main_package_dir = os.path.dirname(__file__)


class Hooks(object):

    default_mesgs = {'agilent_set_fm_ext': {'freq': 40e6,
                                            'peak_freq_dev': 40e6,
                                            'amplitude': 0.7,
                                            'output_state': True},
                     'agilent_set_burst': {'freq': 500e3,
                                           'amplitude': 3.0,
                                           'period': 1e-3,
                                           'output_state': True},
                     'agilent_set_freq_sweep': {'start_freq': 1e6,
                                                'stop_freq': 400e3,
                                                'sweep_time': 10e-3,
                                                'amplitude': 5.0,
                                                'output_state': True},
                     'agilent_set_continuous': {'freq': 700e3,
                                                'amplitude': 0.2,
                                                'offset': 0.0,
                                                'output_state': True},
                     'agilent_set_arbitrary': {'freq': 150e3,
                                                'low_volt': 0.0,
                                                'high_volt': 0.5,
                                                'output_state': True},
                     'agilent_set_output': {'state': True},
                     'dds_set_freq': {'freq': 80000000,
                                      'ch': 'A'},
                     'dds_set_amp': {'amp': 1, 'ch': 'A'},
                     'dds_set_freq_and_amp': {'ch': 'A', 'amp': 50,
                                              'freq': 80000000},
                     'dds_set_a_and_b': {'a_freq': 80000000,
                                         'b_freq': 80000000,
                                         'a_amp': 50,
                                         'b_amp': 50},
                     'dds_sweep_freq': {'low_freq': 80000000,
                                        'high_freq': 80500000,
                                        'step_size': 10,
                                        'step_time': 1000,
                                        'ch': 'A'},
                     'dds_sweep_freq_for_humans': {'ch': 'A',
                                                   'low_freq': 80000000,
                                                   'high_freq': 80500000,
                                                   'sweep_time(s)': 3.0e-3,
                                                   'step_size(Hz)': 10},
                     'test_sleep': {'sleep_time_ms': 1.0},
                     'tek_scope_trace': {'file_path': 'E:\\traces.logs',
                                        'channel': 1},
                    'tek_scope_usb_trace': {'file_path': 'E:\\traces.logs',
                                        'channel': 1},
                    'agilentN900A_marker': {'file_path': 'E:\\traces.logs',
                                        'channel': 1},
                     'ESDcontroller_readerrors': {},
                     'ESDcontroller_move_position': {'abs_pos': 0.0,
                                                    'axis': 3},
                     'mw_set_freq': {'freq': 6000.0,
                                      'ch': '0'},
                     'mw_set_amp': {'amp': 20000,
                                      'ch': '0'},
                     'mw_set_phase': {'phase': 10,
                                      'ch': '0'},
                      'mw_query_settings': {'ch': 0},
                     'extESP300_set_position': {'axis': 2,
                                      'position': -0.095},
                     'StanfordMW_enable_output': {'state': True},
                     'StanfordMW_disable_all': {'disable': False},
                     'StanfordMW_continuous': {'freq(Hz)': 6.8e9,
                                               'amplitude(dBm)': 0.0,
                                               'offset(V)': 0.0,
                                               'output_state': True},
                     'StanfordMW_continuous_Vpp': {'freq(Hz)': 1.0e3,
                                               'amplitude(Vpp)': 0.0,
                                               'offset(V)': 0.0,
                                               'output_state': True},
                     'StanfordMW_FM_ext': {'freq(Hz)': 6.8e9,
                                           'amplitude(dBm)': 0.0,
                                           'offset(V)': 0.0,
                                           'output_state': True},
                     'StanfordMW_freqsweep_ext': {'amplitude(dBm)': 0.0,
                                                  'sweep_low_end(Hz)': 5e9,
                                                  'sweep_high_end(Hz)': 5.5e9,
                                                  'offset(V)': 0.0,
                                                  'output_state': True},
                     'StanfordMW_trigger_ListMode': {},
                     'rigol_set_continuous': {'freq': 700e3,
                                                'amplitude': 0.1,
                                                'offset': 0.0,
                                                'phase':0.0,
                                                'channel':2},
                     'rigol_set_output': {'state': False,
                                          'channel':2},
                     'agilentN900A_trigger_marker': {'num_avg': 100,
                                        			 'freq(GHz)': 6.83468,
                                        			 'span(MHz)': 25,
                                        			 'ref_level(dBm)': 15}
                    }

    # def drop_down_test(self, mesg_dict):
    #     print mesg_dict

    def agilentN900A_trigger_marker(self, mesg_dict):
        logging.info('HOOK:Agilent_N900A: setup triggering of marker')
        num_avg = mesg_dict['num_avg']
        freq = mesg_dict['freq(GHz)']
        span = mesg_dict['span(MHz)']
        ref_lev = mesg_dict['ref_level(dBm)']
        agilentN900A.trigger_marker_avg(num_avg,freq,span,ref_lev)

    def rigol_set_output(self, mesg_dict):
        logging.info('HOOK:rigolDG1022Z: setting output: ' +
              str(mesg_dict['state']))
        rigolDG1022Z.set_output(**mesg_dict)

    def rigol_set_continuous(self, mesg_dict):
        logging.info('HOOK:rigolDG1022Z: setting continuous mode')
        rigolDG1022Z.set_continuous(**mesg_dict)

    def StanfordMW_trigger_ListMode(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: Trigger ListMode iterator.')
        stanfordSG384.trigger_ListMode()

    def StanfordMW_enable_output(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: setting output' +
              str(mesg_dict['state']))
        stanfordSG384.set_output(**mesg_dict)

    def StanfordMW_disable_all(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: disabling output is' +
              str(mesg_dict['disable']))
        stanfordSG384.disable_all(**mesg_dict)

    def StanfordMW_continuous(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: setting to continuous mode')
        freq = mesg_dict['freq(Hz)']
        amplitude = mesg_dict['amplitude(dBm)']
        offset = mesg_dict['offset(V)']
        output_state = mesg_dict['output_state']
        stanfordSG384.set_continuous(freq, amplitude, offset, output_state)

    def StanfordMW_continuous_Vpp(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: setting to continuous mode with amp. in voltage')
        freq = mesg_dict['freq(Hz)']
        amplitude = mesg_dict['amplitude(Vpp)']
        offset = mesg_dict['offset(V)']
        output_state = mesg_dict['output_state']
        stanfordSG384.set_continuous_Vpp(freq, amplitude, offset, output_state)

    def StanfordMW_FM_ext(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: setting to external FM mode')
        freq = mesg_dict['freq(Hz)']
        amplitude = mesg_dict['amplitude(dBm)']
        offset = mesg_dict['offset(V)']
        peak_freq_dev = mesg_dict['peakdev(Hz)']
        output_state = mesg_dict['output_state']
        stanfordSG384.set_fm_ext(freq, amplitude, offset, peak_freq_dev, output_state)

    def StanfordMW_freqsweep_ext(self, mesg_dict):
        logging.info('HOOK:Stanford_SG384: setting to external freq. sweep mode')
        amplitude = mesg_dict['amplitude(dBm)']
        sweep_low_end = mesg_dict['sweep_low_end(Hz)']
        sweep_high_end = mesg_dict['sweep_high_end(Hz)']
        offset = mesg_dict['offset(V)']
        output_state = mesg_dict['output_state']
        stanfordSG384.set_freqsweep_ext(amplitude, sweep_low_end, sweep_high_end, offset, output_state)

    def agilentN900A_marker(self, mesg_dict):
        logging.info('HOOK:Agilent_N900A: marker')
        agilentN900A.get_n_save_marker_pos(**mesg_dict)

    def mw_set_freq(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: set_freq: ' +
                  str(mesg_dict))
            mw_client.set_freq(mesg_dict)

    def mw_set_amp(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: set_amp: ' +
                  str(mesg_dict))
            mw_client.set_amp(mesg_dict)

    def mw_set_freq(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: set_freq: ' +
                  str(mesg_dict))
            mw_client.set_freq(mesg_dict)

    def mw_set_phase(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: set_phase: ' +
                  str(mesg_dict))
            mw_client.set_phase(mesg_dict)

    def mw_query_settings(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: query_settings: ' +
                  str(mesg_dict))
            mw_client.query_settings(mesg_dict)

    def mw_set_amp(self, mesg_dict):
        if ENABLE_MW:
            logging.info('HOOK:mw: set_amp: ' +
                  str(mesg_dict))
            mw_client.set_amp(mesg_dict)

    def extESP300_set_position(self, mesg_dict):
        if ENABLE_extGPIB:
            logging.info('HOOK:ESP300: set_position: ' +
                  str(mesg_dict))
            extGPIB_client.set_position(mesg_dict)

    # def ESDcontroller_readerrors(self, mesg_dict):
    #     logging.info('HOOK:Newport_ESP300: Read errors. ')
    #     newportesp300.read_all_errors()

    # def ESDcontroller_move_position(self, mesg_dict):
    #     logging.info('HOOK:Newport_ESP300: Move axis ' +
    #         str(mesg_dict['axis']) + ' to ' + str(mesg_dict['abs_pos']))
    #     newportesp300.move_absposition(**mesg_dict)

    def tek_scope_trace(self, mesg_dict):
        logging.info('HOOK:Tektronix_TDS1002: acquire trace: ch: ' +
              str(mesg_dict['channel']))
        tektronixTDS1002.get_save_data(**mesg_dict)

    def tek_scope_usb_trace(self, mesg_dict):
        logging.info('HOOK:Tektronix_TDS2012C: acquire trace: ch: ' +
              str(mesg_dict['channel']))
        tektronixTDS2012C.get_save_data(**mesg_dict)

    def test_sleep(self, mesg_dict):
        time_s = mesg_dict['sleep_time_ms']/1000.0
        logging.info('HOOK:Sleeping for {0} seconds'.format(time_s))
        time.sleep(time_s)

    def agilent_set_fm_ext(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: set to FM External modulation.')
        agilent_33250a.set_fm_ext(**mesg_dict)

    def agilent_set_output(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: setting output: ' +
              str(mesg_dict['state']))
        agilent_33250a.set_output(**mesg_dict)

    def agilent_set_burst(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: setting burst mode')
        agilent_33250a.set_burst(**mesg_dict)

    def agilent_set_freq_sweep(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: setting freq sweep mode')
        agilent_33250a.set_freq_sweep(**mesg_dict)

    def agilent_set_continuous(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: setting continuous mode')
        agilent_33250a.set_continuous(**mesg_dict)

    def agilent_set_arbitrary(self, mesg_dict):
        logging.info('HOOK:agilent_33250a: setting continuous arbitrary waveform mode')
        agilent_33250a.set_arbitrary(**mesg_dict)

    def dds_set_freq(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:dds_comb: set_freq: ' +
                  str(mesg_dict))
            dds_client.set_freq(mesg_dict)

    def dds_set_amp(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:dds_comb: set_amp: ' +
                  str(mesg_dict))
            dds_client.set_amp(mesg_dict)

    def dds_set_freq_and_amp(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:dds_comb: set_freq_amd_amp: ' +
                  str(mesg_dict))
            dds_client.set_freq(mesg_dict)
            dds_client.set_amp(mesg_dict)

    def dds_set_a_and_b(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:dds_comb: Setting amplitude and voltage of channel A and B')
            mesg1 = {'ch': 'A',
                     'amp': mesg_dict['a_amp'],
                     'freq': mesg_dict['a_freq']}
            mesg2 = {'ch': 'B',
                     'amp': mesg_dict['b_amp'],
                     'freq': mesg_dict['b_freq']}
            dds_client.set_freq(mesg1)
            dds_client.set_amp(mesg1)

            dds_client.set_freq(mesg2)
            dds_client.set_amp(mesg2)

    def dds_sweep_freq(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:Setting DDS Sweep Frequency')
            dds_client.sweep_freq(mesg_dict)

    def dds_sweep_freq_for_humans(self, mesg_dict):
        if ENABLE_DDS:
            logging.info('HOOK:DDS Sweep for humans')
            step_size = mesg_dict['step_size(Hz)']
            sweep_time = mesg_dict['sweep_time(s)']
            low_freq = mesg_dict['low_freq']
            high_freq = mesg_dict['high_freq']
            n_steps = (high_freq - low_freq)/step_size
            step_time = int(sweep_time/n_steps*1e9)
            out_mesg = {'low_freq': low_freq,
                        'high_freq': high_freq,
                        'ch': mesg_dict['ch'],
                        'step_size': step_size,
                        'step_time': step_time}
            print(out_mesg)
            dds_client.sweep_freq(out_mesg)

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
            if not self.ramp_generated:
                try:
                    self.current_data = self.data_q.get(True, 0.05)
                    self.prev_data_list.append(self.current_data)
                    logging.info('New task received')
                except Queue.Empty:
                    pass
                else:
                    # there is data in the queue, which means there is a task
                    # pending to be done
                    logging.info('Making ramps')
                    start_making_time = datetime.datetime.now()
                    self.ramp_out = make_ramps(self.current_data)
                    end_making_time = datetime.datetime.now()
                    dt = end_making_time - start_making_time
                    logging.info('Took {0} to make ramps'.format(dt))
                    self.ramp_generated = True

            if self.task_running:
                # check if task is done
                if self.digital_task.is_task_done:
                    self.task_running = False
                    self.task_end_time = datetime.datetime.now()
                    self.waiting_after_running = True
                    self.log_ramps()

                    logging.info('Task done')
                    dt = self.task_end_time - self.task_start_time
                    logging.info('Task running length {0}'.format(dt))

            elif self.waiting_after_running:
                delta_t = datetime.datetime.now() - self.task_end_time
                time_elapsed_after_task_end = delta_t.total_seconds()*1000
                if time_elapsed_after_task_end > self.wait_time_after_running:
                    logging.info('Waiting time is : ' + str(self.wait_time_after_running))
                    logging.info('Waited for {0} ms'.format(time_elapsed_after_task_end))
                    self.waiting_after_running = False

            elif self.ramp_generated:
                properties = self.prev_data_list[0]['properties']
                if 'wait_after_running' in properties:
                    self.wait_time_after_running = properties['wait_after_running']
                else:
                    self.wait_time_after_running = 0.0
                self.clear_tasks()
                # if not, and if we have a generated ramp, upload it and run

                self.upload_and_start_tasks()

                logging.info('Task started at {0}'.format(self.task_start_time))

                self.task_running = True
                self.ramp_generated = False

    def log_ramps(self):
        log_data = self.prev_data_list.pop(0)
        if 'log_ramp_file' in log_data['properties']:
            if not log_data['properties']['log_ramp_file']:
                return
        dt = self.task_end_time - self.task_start_time
        # modify it temporarily to be able to run short ramps
        if(dt.total_seconds() < 0.1):
        #if(dt.total_seconds() < 15.0):
            logging.error('Task ran for less than 15 seconds.')
            # publish the error so that anyone waiting for an image can catch
            # it and take action
            pub_socket.send('server_error Task ran for less than 15 seconds')
        else:
            # pub_socket.send('server_error OK')
            pass
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
        logging.info('Clearing tasks')
        if self.digital_task is not None:
            self.dev1_task.ClearTask()
            self.dev2_task.ClearTask()
            self.dev3_task.ClearTask()
            self.dev4_task.ClearTask()
            self.digital_task.ClearTask()
            # print('Reseting clock to high')
            # daq.reset_analog_sample_clock(False)

    def upload_and_start_tasks(self):
        daq.reset_analog_sample_clock()
        out = self.ramp_out
        dev1_task, dev2_task, dev3_task, dev4_task, digital_task = daq.create_all_tasks(*out)
        dev1_task.StartTask()
        dev2_task.StartTask()
        dev3_task.StartTask()
        dev4_task.StartTask()
        digital_task.StartTask()
        self.dev1_task = dev1_task
        self.dev2_task = dev2_task
        self.dev3_task = dev3_task
        self.dev4_task = dev4_task
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
    line_ids = [line_fmt.format(n) for n in range(5, 31)]
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

def dev4_analog_ids():
    return get_analog_ids("Dev4")

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

    # The channels used are Dev1/port0/line5:31
    dig_channels = get_digital_channels(channel_list)

    for line_number, dig_ch in zip(range(5, 31), dig_channels):
        time, ramp_uint = dig_ch.generate_ramp(time_div=jump_resolution)
        if line_number == 5:
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

    # check for timing overlap in keyframelist
    error_keyname = keyframe_list.do_keyframes_overlap()
    if error_keyname is not None:
        error_fmt = '{0} overlaps with the next keyframe'
        error_str = error_fmt.format(error_keyname)
        error_list.append(error_str)


    return error_list


def make_ramps(data):
    digital_data = make_digital_ramps(data)
    dev1_trigger_line, dev1_voltages = make_analog_ramps(data, dev_name="Dev1")
    dev2_trigger_line, dev2_voltages = make_analog_ramps(data, dev_name="Dev2")
    dev3_trigger_line, dev3_voltages = make_analog_ramps(data, dev_name="Dev3")
    dev4_trigger_line, dev4_voltages = make_analog_ramps(data, dev_name="Dev4")
    callback_list = make_callback_list(data)
    return (digital_data, dev1_trigger_line, dev1_voltages,
            dev2_trigger_line, dev2_voltages, dev3_trigger_line,
            dev3_voltages, dev4_trigger_line, dev4_voltages, callback_list)


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
