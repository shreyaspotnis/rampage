import visa
import time

resource_manager = visa.ResourceManager()


class Aglient33250A(object):

	def __init__(self):
		self.instr = self.open_instrument()		

	def open_instrument(self):
		resource_list = resource_manager.list_resources()
		gpib_address_list = filter(lambda x: x[:4]=='GPIB', resource_list)

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
		commands = ['FUNC SHAP SIN'  # set to output sine functions
					'FM:SOUR EXT',
					'FM:FREQ {0}'.format(freq),
					'FM:DEV {0}'.format(peak_freq_dev),
					'VOLT {0}'.format(amplitude),
					'FM:STAT ON']	 # set to frequency modulation
		if output_state is True:
			commands.append('OUTP ON')
		else:
			commands.append('OUTP OFF')

		command_string = '\n'.join(commands)
		self.instr.write(command_string)


class GPIBError(Exception):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)


#globals
agilent_33250a = Aglient33250A()
