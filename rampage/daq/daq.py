import PyDAQmx.DAQmxTypes as daqtypes
import PyDAQmx as pydaq
import ctypes
import numpy as np
import datetime


class ExptSettings(object):
    external_clock_line = "/Dev1/PFI8"
    max_expected_rate = 1000000  # Hz
    dev2_clock_line = "/Dev1/PFI3"
    dev3_clock_line = "/Dev1/PFI4"
    dev2_clock_out = 31
    dev2_clock_out_name = "Dev1/port0/line31"
    dev3_clock_out = 27
    dev3_clock_out_name = "Dev1/port0/line27"
    callback_resolution = 10e-3  # (ms)
    ext_clock_frequency = 250e3  # (Hz)

expt_settings = ExptSettings()


def print_device_info(dev_name):
    """Prints information about the given device.

    Usage:
    print_device_info("Dev1")
    """
    string_buffer = ctypes.create_string_buffer(1024)
    attributes = [pydaq.DAQmx_Dev_ProductType, pydaq.DAQmx_Dev_SerialNum,
                  pydaq.DAQmx_Dev_AO_PhysicalChans,
                  pydaq.DAQmx_Dev_CI_PhysicalChans,
                  pydaq.DAQmx_Dev_CO_PhysicalChans,
                  pydaq.DAQmx_Dev_DO_Lines]
    attribute_names = ['DAQmx_Dev_ProductType',
                       'DAQmx_Dev_SerialNum',
                       'DAQmx_Dev_AO_PhysicalChans',
                       'DAQmx_Dev_CI_PhysicalChans',
                       'DAQmx_Dev_CO_PhysicalChans',
                       'DAQmx_Dev_DO_Lines']
    ret_values = []
    for a in attributes:
        pydaq.DAQmxGetDeviceAttribute(dev_name, a, string_buffer)
        ret_values.append(str(string_buffer.value))

    print('Device Name:\t' + dev_name)
    for n, v in zip(attribute_names, ret_values):
        print '\t' + n + ':\t' + v


def get_device_name_list():
    """Returns a list of device names installed."""
    dev_names = ctypes.create_string_buffer(1024)
    pydaq.DAQmxGetSysDevNames(dev_names, len(dev_names))
    return dev_names.value.split(', ')


def print_all_device_info():
    """Prints info on all devices."""
    for dev in get_device_name_list():
        print_device_info(dev)


def reset_analog_sample_clock(state=False):
    """Reset the clock line.

    Use this just before starting a run to avoid timing issues.
    """
    set_digital_line_state(expt_settings.dev2_clock_out_name, state)
    set_digital_line_state(expt_settings.dev3_clock_out_name, state)


def set_digital_line_state(line_name, state):
    """Set the state of a single digital line.

    line_name (str) - The physical name of the line.
        e.g line_name="Dev1/port0/line3"
        This should be a single digital line. Specifying more than one would
        result in unexpected behaviour. For example "Dev1/port0/line0:5" is
        not allowed.
        see http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/physchannames/
        for details of naming lines.
    state (bool) - state=True sets the line to high, state=False sets to low.

    """
    # get the line number from the line name. Thats the number of bits to shift
    bits_to_shift = int(line_name.split('line')[-1])
    dig_data = np.ones(2, dtype="uint32")*bool(state)*(2**bits_to_shift)
    # Note here that the number of samples written here are 2, which is the
    # minimum required for a buffered write. If we configure a timing for the
    # write, it is considered buffered.
    # see http://zone.ni.com/reference/en-XX/help/370471Y-01/daqmxcfunc/daqmxwritedigitalu32/
    DigitalOutputTask(line_name, dig_data).StartAndWait()

    # create_digital_output_task(line_name, dig_data)


class DigitalOutputTask(pydaq.Task):
    """A digital output task.

    Arguments
    ---------

    lines (str) - The physical names of the lines used in the task.
        e.g line_name="Dev1/port0/line8:31"
        see http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/physchannames/
        for details of naming lines.

    digital_data (numpy.array of uint32) -
        The length of the array is the number of samples

    name_for_lines(str) - optional name to refer to the lines specified.

    ext_clock_line(str) - Name of the line where the external clock is
        connected.

    Usage
    -----
    dig_chn = DigitalOutputTask(...)
    dig_chn.StartTask()
    dig_chn.WaitUntilTaskDone()
    dig_chn.ClearTask()

    or, alternatively

    DigitalOutputTask(...).StartAndWait()

    """

    def __init__(self, lines, digital_data, name_for_lines=None,
                 ext_clock_line=expt_settings.external_clock_line,
                 auto_configure=True):
        pydaq.Task.__init__(self)
        self.digital_data = digital_data
        self.lines = lines
        self.name_for_lines = name_for_lines
        self.ext_clock_line = ext_clock_line

        if auto_configure:
            self.ConfigureTask()

    def ConfigureTask(self):
        n_written = pydaq.int32()
        n_dig_samples = len(self.digital_data)
        self.CreateDOChan(self.lines, self.name_for_lines,
                          pydaq.DAQmx_Val_ChanForAllLines)
        self.CfgSampClkTiming(self.ext_clock_line,
                              expt_settings.max_expected_rate,
                              pydaq.DAQmx_Val_Rising,
                              pydaq.DAQmx_Val_FiniteSamps, n_dig_samples)
        self.WriteDigitalU32(n_dig_samples, False, -1,
                             pydaq.DAQmx_Val_GroupByChannel,
                             self.digital_data, ctypes.byref(n_written),
                             None)
        # print('Digital n_written', n_written.value)

    def StartAndWait(self):
        """Starts the task and waits until it is done."""
        self.StartTask()
        self.WaitUntilTaskDone(pydaq.DAQmx_Val_WaitInfinitely)
        self.ClearTask()

    def isDone(self):
        """Returns true if task is done."""
        done = pydaq.bool32()
        self.IsTaskDone(ctypes.byref(done))
        return done.value


class DigitalOutputTaskWithCallbacks(DigitalOutputTask):
    """A digital output task.

    Arguments
    ---------

    lines (str) - The physical names of the lines used in the task.
        e.g line_name="Dev1/port0/line8:31"
        see http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/physchannames/
        for details of naming lines.

    digital_data (numpy.array of uint32) -
        The length of the array is the number of samples

    name_for_lines(str) - optional name to refer to the lines specified.

    ext_clock_line(str) - Name of the line where the external clock is
        connected.

    Usage
    -----
    dig_chn = DigitalOutputTask(...)
    dig_chn.StartTask()
    dig_chn.WaitUntilTaskDone()
    dig_chn.ClearTask()

    or, alternatively

    DigitalOutputTask(...).StartAndWait()

    """

    def __init__(self, lines, digital_data, callback_function_list=None,
                 name_for_lines=None,
                 ext_clock_line=expt_settings.external_clock_line):
        DigitalOutputTask.__init__(self, lines, digital_data, name_for_lines,
                                   ext_clock_line, auto_configure=False)

        # calculate number of samples to wait before callback
        n_wait = int(expt_settings.ext_clock_frequency *
                     expt_settings.callback_resolution)
        self.n_wait = n_wait
        self.n_callbacks = 0
        print('n wait', n_wait)
        # pad the digital data. For callbacks to work, the total number of
        # samples to write should be a multiple of the number of samples to wait
        # before a callback. Hence we append the last value of the digital data
        # to itlsef until the length is a multiple
        digital_data = self.padDigitalData(digital_data, n_wait)
        self.digital_data = digital_data

        self.ConfigureTask()
        self.RegisterCallbacks()

        self.is_task_done = False

        # configure callbacks
        if callback_function_list is None:
            self.do_callbacks = False
        elif len(callback_function_list) == 0:
            self.do_callbacks = False
        else:
            self.do_callbacks = True

            self.latest_callback_index = 0

            out = callback_function_list[self.latest_callback_index]
            callback_time = out[0]
            self.callback_step = callback_time/expt_settings.callback_resolution
            self.callback_funcs = out[1]

            self.callback_function_list = callback_function_list


    def RegisterCallbacks(self):
        self.AutoRegisterEveryNSamplesEvent(pydaq.DAQmx_Val_Transferred_From_Buffer,
                                            self.n_wait, 0)
        self.AutoRegisterDoneEvent(0)

    def padDigitalData(self, dig_data, n):
        """Pad dig_data with its last element so that the new array is a
        multiple of n.
        """
        n = int(n)
        l0 = len(dig_data)
        if l0 % n == 0:
            return dig_data  # no need of padding
        else:
            ladd = n - (l0 % n)
            dig_data_add = np.zeros(ladd, dtype="uint32")
            dig_data_add.fill(dig_data[-1])
            return np.concatenate((dig_data, dig_data_add))

    def EveryNCallback(self):
        """Called by PyDAQmx whenever a callback event occurs."""
        # print('ncall ', self.n_callbacks)
        if self.do_callbacks:
            if self.n_callbacks >= self.callback_step:
                # print('n_callbacks', self.n_callbacks)
                for func, func_dict in self.callback_funcs:
                    func(func_dict)

                self.latest_callback_index +=1
                if self.latest_callback_index >= len(self.callback_function_list):
                    # print('done with callbacks')
                    self.do_callbacks = False
                else:
                    out = self.callback_function_list[self.latest_callback_index]
                    callback_time = out[0]
                    self.callback_step = int(callback_time/expt_settings.callback_resolution)
                    # print('updatin callback step', self.callback_step)
                    self.callback_funcs = out[1]

        self.n_callbacks += 1
        #print('n_callbacks', self.n_callbacks)
        return 0  # The function should return an integer

    def DoneCallback(self, status):
        """Called whenever the task is done."""
        print "Status, done", status
        self.is_task_done = True
        return 0  # The function should return an integer


class ContinuousAnalogOutputTask(pydaq.Task):
    def __init__(self, analog_lines, analog_data, n_samples, sample_rate,
                 name_for_channel=None,
                 clock_line=expt_settings.dev2_clock_line):
        pydaq.Task.__init__(self)
        n_written = pydaq.int32()

        # print('analog lines')
        self.CreateAOVoltageChan(analog_lines, None, -10.0, 10.0,
                                 pydaq.DAQmx_Val_Volts, None)
        # print('analog lines2')
        self.CfgSampClkTiming(None, sample_rate,
                              pydaq.DAQmx_Val_Rising,
                              pydaq.DAQmx_Val_ContSamps,
                              n_samples)
        self.CfgDigEdgeStartTrig(expt_settings.dev2_clock_line,
                                 pydaq.DAQmx_Val_Rising)
        self.WriteAnalogF64(n_samples, False, -1,
                            pydaq.DAQmx_Val_GroupByScanNumber, analog_data,
                            ctypes.byref(n_written), None)
        # print('Analog n_written', n_written.value)


class FiniteAnalogOutputTask(pydaq.Task):
    """An analog output task for outputting finite samples.
    This task uses a sample clock and changes the voltage at the analog outputs
    whenever there is a rising edge at the clock.

    Arguments
    ---------

    analog_lines (str) - The physical names of the lines used in the task.
        e.g line_name="Dev2/ao0:7"
        see http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/physchannames/
        for details of naming lines.

    analog_data (numpy.array of float64) -
        The length of the array is n_samples * n_channels
        The data should be formatted in a certain way. For example, if you have
        two channels A and B, and 5 samples, the ordering of the data is -
        A0, B0, A1, B1,..., A4, B4.

    name_for_lines(str) - optional name to refer to the lines specified.

    ext_clock_line(str) - Name of the line where the external clock is
        connected.
    """

    def __init__(self, analog_lines, analog_data, n_samples,
                 name_for_channel=None,
                 clock_line=expt_settings.dev2_clock_line):
        pydaq.Task.__init__(self)

        n_written = pydaq.int32()

        self.CreateAOVoltageChan(analog_lines, None, -10.0, 10.0,
                                 pydaq.DAQmx_Val_Volts, None)
        self.CfgSampClkTiming(clock_line, expt_settings.max_expected_rate,
                              pydaq.DAQmx_Val_Rising,
                              pydaq.DAQmx_Val_FiniteSamps,
                              n_samples)
        self.WriteAnalogF64(n_samples, False, -1,
                            pydaq.DAQmx_Val_GroupByScanNumber, analog_data,
                            ctypes.byref(n_written), None)
        # print('Analog n_written', n_written.value)


def create_all_tasks(digital_data, dev2_trigger_line, dev2_voltages,
                     dev3_trigger_line, dev3_voltages, callback_list):

    # create Dev2 Task
    _, n_dev2_samples = dev2_voltages.shape
    dev2_task = FiniteAnalogOutputTask("Dev2/ao0:7", dev2_voltages.T.flatten(),
                                       n_dev2_samples,
                                       clock_line=expt_settings.dev2_clock_line)

    _, n_dev3_samples = dev3_voltages.shape
    dev3_task = FiniteAnalogOutputTask("Dev3/ao0:7", dev3_voltages.T.flatten(),
                                       n_dev3_samples,
                                       clock_line=expt_settings.dev3_clock_line)

    digital_data += dev2_trigger_line*(2**expt_settings.dev2_clock_out)
    digital_data += dev3_trigger_line*(2**expt_settings.dev3_clock_out)

    # digital_task = DigitalOutputTask("Dev1/port0/line8:31", digital_data)
    digital_task = DigitalOutputTaskWithCallbacks("Dev1/port0/line8:31",
                                                  digital_data, callback_list)

    return dev2_task, dev3_task, digital_task


def p24_pulse_train(n_samples=100):
    """Sends a pulse train of on-off in Dev1/port0/line24.

    This function creates a task, starts it and waits until it is over.
    Uses expt_settings.external_clock_line as a clock.

    n_samples - number of on off samples.
    """
    samples = (np.arange(n_samples, dtype="uint32") % 2)*(2**24)
    samples[-1] = 0
    DigitalOutputTask("Dev1/port0/line24", samples).StartAndWait()


def write_analog_channel(time_array, voltage_array, analog_lines="Dev2/ao0",
                         time_base=4e-3):

    n_dig_samples = int(time_array[-1]/time_base) + 2
    n_ana_samples = len(time_array)
    timing_line_number = 31
    sample_locations = np.array(time_array/time_base, dtype=int)
    timing_channel_data = np.zeros(n_dig_samples, dtype="uint32")
    timing_channel_data[sample_locations] = 2**timing_line_number

    # add a trigger on p24 at the very end
    p24_channel_data = np.zeros(n_dig_samples, dtype="uint32")
    # p24_channel_data[-2] = 2**24
    p24_channel_data[0] = 2**24
    # p24_channel_data[zero_index*2] = 2**24
    # p24_channel_data = (np.arange(n_dig_samples, dtype="uint32") % 2)*(2**24)
    #timing_channel_data[-1] = 0


    digital_data = timing_channel_data + p24_channel_data

    sample_rate = 10000
    n_cont_samples = int((n_dig_samples - 2)*time_base*sample_rate/1000)
    # print('n_cont_samples', n_cont_samples)
    test_cont_samples = np.arange(n_cont_samples*1.0)
    test_cont_samples /= test_cont_samples[-1]
    test_cont_samples[-1] = 0.0

    ana_cont_task = ContinuousAnalogOutputTask("Dev3/ao0", test_cont_samples,
                                               len(test_cont_samples),
                                               sample_rate)
    ana_cont_task.StartTask()

    ana_task = FiniteAnalogOutputTask(analog_lines, voltage_array,
                                      n_ana_samples)
    ana_task.StartTask()

    DigitalOutputTaskWithCallbacks("Dev1/port0/line24, Dev1/port0/line31",
                      digital_data).StartAndWait()
    # create_digital_output_task("Dev1/port0/line24, Dev1/port0/line31",
    #                            digital_data)


if __name__ == '__main__':
    #p24_pulse_train(100)
    # time_array = np.array([1, 10, 15, 25000], dtype=float)*4e-3
    # voltage_array = np.array([1., 0., 3., 0.0])
    #time_array = np.array([0., 3000.], dtype=float)*8e-3
    time_array = np.array([0., (int(50./8e-3))*8e-3], dtype=float)
    # zero_index = 2050
    print('Time array shape:', time_array.shape)
    voltage_list = [np.zeros(time_array.shape, dtype=float) for i in range(8)]
    #voltage_list[0] = np.sin(time_array*2.0*np.pi*1e-1)
    #voltage_list[1] = time_array/np.max(time_array)
    # voltage_list[0][-1] = 0.0
    #voltage_list[1][-100:] = 0.0
    # voltage_list[1][-3:] = 0.0
    voltage_list[1] = np.array([2., 0.])
    # voltage_list[1][0] = 1.0
    voltages = np.vstack(voltage_list).T.flatten()
    write_analog_channel(time_array, voltages, analog_lines="Dev2/ao0:7")
