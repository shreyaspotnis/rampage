import visa
import numpy as np
import logging
from datetime import datetime

resource_manager = visa.ResourceManager()


class Aglient33250A(object):

    def __init__(self):
        self.instr = self.open_instrument()

    def open_instrument(self):
        resource_list = resource_manager.list_resources()
        gpib_address_list = filter(lambda x: x[:4] == 'GPIB', resource_list)

        for addr in gpib_address_list:
            instr = resource_manager.open_resource(addr)
            idn = instr.query('*IDN?')
            if 'Agilent Technologies,33250A' in idn:
                    return instr
        else:
            raise GPIBError('Aglient33250A function generator not in GPIB device list')
            # device not round raise exception

    def set_output(self, state):
        """Sets whether the function generator is outputting a voltage."""
        if state:
            self.instr.write('OUTP ON')
        else:
            self.instr.write('OUTP OFF')

    def set_fm_ext(self, freq, amplitude, peak_freq_dev=None,
                   output_state=True):
        """Sets the func generator to frequency modulation with external modulation.
        freq is the carrier frequency in Hz."""

        if peak_freq_dev is None:
            peak_freq_dev = freq
        commands = ['FUNC SIN',  # set to output sine functions
                    'FM:STAT ON',
                    'FREQ {0}'.format(freq),
                    'FM:SOUR EXT',
                    # 'FM:FREQ {0}'.format(freq),
                    'FM:DEV {0}'.format(peak_freq_dev),
                    'VOLT {0}'.format(amplitude),
                    'VOLT:OFFS 0']   # set to frequency modulation
        if output_state is True:
            commands.append('OUTP ON')
        else:
            commands.append('OUTP OFF')
        command_string = '\n'.join(commands)
        print_string = '\n\t' + command_string.replace('\n', '\n\t')
        logging.info(print_string)
        self.instr.write(command_string)
        # self.read_all_errors()

    def set_burst(self, freq, amplitude, period, output_state=True):
        """Sets the func generator to burst mode with external trigerring."""

        ncyc = int(period*freq)
        commands = ['FUNC SIN',
                    'BURS:STAT ON',
                    'BURS:MODE TRIG',  # external trigger
                    'TRIG:SOUR EXT',
                    'TRIG:SLOP POS',
                    'FREQ {0}'.format(freq),
                    'VOLT {0}'.format(amplitude),
                    'VOLT:OFFS 0',
                    'BURS:NCYC {0}'.format(ncyc)]
        if output_state is True:
            commands.append('OUTP ON')
        else:
            commands.append('OUTP OFF')

        command_string = '\n'.join(commands)
        print_string = '\n\t' + command_string.replace('\n', '\n\t')
        logging.info(print_string)
        self.instr.write(command_string)

        # self.read_all_errors()

    def set_continuous(self, freq, amplitude, offset, output_state=True):
        """Programs the function generator to output a continuous sine wave."""
        commands = ['FUNC SIN',
                    'BURS:STAT OFF',
                    'SWE:STAT OFF',
                    'FM:STAT OFF',
                    'FREQ {0}'.format(freq),
                    'VOLT {0}'.format(amplitude),
                    'VOLT:OFFS {0}'.format(offset),
                    ]
        if output_state is True:
            commands.append('OUTP ON')
        else:
            commands.append('OUTP OFF')

        command_string = '\n'.join(commands)
        print_string = '\n\t' + command_string.replace('\n', '\n\t')
        logging.info(print_string)
        self.instr.write(command_string)

        # self.read_all_errors()

    def set_freq_sweep(self, start_freq, stop_freq, sweep_time, amplitude,
                       output_state=True):
        commands = ['FUNC SIN',
                    'TRIG:SOUR EXT',
                    'TRIG:SLOP POS',
                    'SWE:STAT ON',
                    'FREQ:STAR {0}'.format(start_freq),
                    'FREQ:STOP {0}'.format(stop_freq),
                    'SWE:TIME {0}'.format(sweep_time),
                    'VOLT {0}'.format(amplitude),
                    'VOLT:OFFS 0',
                    'SWE:STAT ON']
        if output_state is True:
            commands.append('OUTP ON')
        else:
            commands.append('OUTP OFF')

        command_string = '\n'.join(commands)
        print_string = '\n\t' + command_string.replace('\n', '\n\t')
        logging.info(print_string)
        self.instr.write(command_string)

    def read_all_errors(self):
        done = False
        while not done:
            err = self.instr.query('SYST:ERR?')
            print(err)
            if err[:2] == '+0':
                done = True


class TektronixTDS1002(object):

    def __init__(self):
        self.instr = self.open_instrument()

    def open_instrument(self):
        resource_list = resource_manager.list_resources()
        gpib_address_list = filter(lambda x: x[:4] == 'GPIB', resource_list)

        for addr in gpib_address_list:
            instr = resource_manager.open_resource(addr)
            idn = instr.query('*IDN?')
            if 'TEKTRONIX,TDS 1002' in idn:
                return instr
        else:
            raise GPIBError('TektronicsTDS1002 oscilloscope not in GPIB device list')
            # device not round raise exception

    def get_data(self, channel=1):
        hor_pos = float(self.instr.query('HOR:MAI:POS?'))
        hor_scale = float(self.instr.query('HOR:MAI:SCA?'))
        ch1_pos = float(self.instr.query('CH{0}:POS?'.format(channel)))
        ch1_sca = float(self.instr.query('CH{0}:SCA?'.format(channel)))
        commands = ['DATA:WIDTH 1',
                    'DATA:STAR 1',
                    'DATA:STOP 2500',
                    'DATA:SOU CH{0}'.format(channel),
                    'CURV?']
        command_string = '\r\n'.join(commands)
        self.instr.write(command_string)
        # the first 6 bytes are #42500 and the last byte is \n
        # ignore those
        data = self.instr.read_raw()[6:-1]
        data = np.fromstring(data, dtype=np.int8)
        data_scaled = (np.array(data, dtype='float')*(10.0/2**8) - ch1_pos)*ch1_sca
        time_array = np.arange(len(data_scaled), dtype='float')*10.0*hor_scale/len(data_scaled)
        return time_array, data_scaled

    def get_save_data(self, file_path, channel=1):
        hor_pos = float(self.instr.query('HOR:MAI:POS?'))
        hor_scale = float(self.instr.query('HOR:MAI:SCA?'))
        ch1_pos = float(self.instr.query('CH{0}:POS?'.format(channel)))
        ch1_sca = float(self.instr.query('CH{0}:SCA?'.format(channel)))
        commands = ['DATA:WIDTH 1',
                    'DATA:STAR 1',
                    'DATA:STOP 2500',
                    'DATA:SOU CH{0}'.format(channel),
                    'CURV?']
        command_string = '\r\n'.join(commands)
        self.instr.write(command_string)
        # the first 6 bytes are #42500 and the last byte is \n
        # ignore those
        data = self.instr.read_raw()[6:-1]
        data = np.fromstring(data, dtype=np.int8)
        data_scaled = (np.array(data, dtype='float')*(10.0/2**8) - ch1_pos)*ch1_sca
        time_array = np.arange(len(data_scaled), dtype='float')*10.0*hor_scale/len(data_scaled)
        np.savetxt(file_path + '\\' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '.txt', (time_array, data_scaled), fmt='%1.4e')
        #return time_array, data_scaled

class NewportESP300(object):

    def __init__(self):
        self.instr = self.open_instrument()

    def open_instrument(self):
        resource_list = resource_manager.list_resources()
        gpib_address_list = filter(lambda x: x[:4] == 'GPIB', resource_list)

        for addr in gpib_address_list:
            instr = resource_manager.open_resource(addr)
            idn = instr.query('*IDN?')
            if 'ESP300 Version' in idn:
                    return instr
        else:
            raise GPIBError('ESP300 Motion Controller not in GPIB device list')
            # device not round raise exception

    def read_position(self, num_axes=2):
        for i in range(num_axes-1):
            pos = self.instr.query(str(i+1)+'TP?')
            print('Pos' + str(i+1) + ' ' + pos[:8])

    def move_absposition(self, abs_pos, axis):
        self.instr.write(str(int(axis))+'PA'+str(abs_pos))
        print('Set Axis ' + str(axis) + ' to ' + abs_pos)

    def read_all_errors(self):
        done = False
        while not done:
            err = self.instr.query('TB?')
            print(err)
            if 'NO ERROR DETECTED' in err:
                done = True

class GPIBError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

#globals
agilent_33250a = Aglient33250A()
# tektronixTDS1002 = TektronixTDS1002()
newportesp300 = NewportESP300()