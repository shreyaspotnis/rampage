"""Provides classes to build arbitrary waveforms."""

import json
import numpy as np


class KeyFrameList(object):

    """Basic timing element.

    Holds a list of keyframes. Each keyframe is a position in time relative to
    a parent keyframe. If parent keyframe is None, then the time is relative
    to the start of the ramp.

    All keyframe data is stored in the dictionary self.dct. Each key in the
    dictionary is a string which is the name of that KeyFrame.

    self.dct has the following structure:
    {
        "key_name_1": {
            "comment": "Info about this keyframe",
            "parent": "another_key_name",
            "time": 10.0
        }
        .
        .
        .
        "key_name_n": {...}
    }

    Additionally, some keyframes can have a "hooks" key, which is also a
    dictionary. Refer to server.Hooks for details.
    """

    def __init__(self, dct=None):
        if dct is None:
            return
        self.dct = dct

        # check all parent keys are actually valid
        for key in self.dct:
            kf = self.dct[key]
            parent_name = kf['parent']
            if parent_name is not None:
                if parent_name not in self.dct:
                    error_string = ('KeyFrame "' + key + '" has a parent "' +
                                    parent_name +
                                    '"" which is not a known KeyFrame')
                    raise KeyError(error_string)
        self.is_baked = False
        # find absolute times for all the keys
        self.bake()

    def bake(self):
        """Find absolute times for all keys.

        Absolute time is stored in the KeyFrame dictionary as the variable
        __abs_time__.
        """
        for key in self.dct:
            self.get_absolute_time(key)
        self.is_baked = True

    def unbake(self):
        """Remove absolute times for all keys."""
        for key in self.dct:
            self.dct[key].pop('__abs_time__', None)
        self.is_baked = False

    def get_absolute_time(self, key):
        """Returns the absolute time position of the key.

        If absolute time positions are not calculated, then this function
        calculates it.
        """
        keyframe = self.dct[key]
        try:
            # if absolute time is already calculated, return that
            return keyframe['__abs_time__']
        except KeyError:
            # if not, calculate by adding relative time to parent's time
            if keyframe['parent'] is None:
                keyframe['__abs_time__'] = keyframe['time']
            else:
                parent_time = self.get_absolute_time(keyframe['parent'])
                abs_time = keyframe['time'] + parent_time
                keyframe['__abs_time__'] = abs_time
            return keyframe['__abs_time__']

    def sorted_key_list(self):
        """Returns list of keys sorted according to their absolute time."""
        if not self.is_baked:
            self.bake()
        key_value_tuple = sorted(self.dct.items(),
                                 key=lambda x: x[1]['__abs_time__'])
        skl = [k[0] for k in key_value_tuple]
        return skl

    def set_time(self, key_name, new_time):
        """Sets the time of key."""
        self.unbake()
        kf = self.dct[key_name]
        kf['time'] = new_time
        self.bake()

    def set_comment(self, key_name, new_comment):
        """Sets the comment of key."""
        kf = self.dct[key_name]
        kf['comment'] = new_comment

    def set_parent(self, key_name, new_parent):
        """Sets the parent of the key."""
        self.unbake()
        kf = self.dct[key_name]
        kf['parent'] = new_parent
        self.bake()

    def set_name(self, old_name, new_name):
        if old_name != new_name:
            self.unbake()
            self.dct[new_name] = self.dct[old_name]
            self.dct.pop(old_name)
            for key in self.dct:
                if self.dct[key]['parent'] == old_name:
                    self.dct[key]['parent'] = new_name
            self.bake()

    def add_keyframe(self, new_key_name, new_key_dict):
        self.unbake()
        self.dct[new_key_name] = new_key_dict
        self.bake()

    def del_keyframe(self, key_name):
        self.unbake()
        kf = self.dct[key_name]
        parent_key = kf['parent']

        # find children of this keyframe
        child_keys = [k for k in self.dct if self.dct[k]['parent'] == key_name]
        # set the parent of child keys to the parent of the deleted key_name
        for ck in child_keys:
            self.dct[ck]['parent'] = parent_key
        # remove the key_name
        self.dct.pop(key_name)
        self.bake()

    def is_ancestor(self, child_key_name, ancestor_key_name):
        """Returns True if ancestor lies in the ancestry tree of child."""

        # all keys are descendents of None
        if ancestor_key_name is None:
            return True

        one_up_parent = self.dct[child_key_name]['parent']
        if child_key_name == ancestor_key_name:
            # debatable semantics, but a person lies in his/her own
            # ancestry tree
            return True
        elif one_up_parent is None:
            return False
        else:
            return self.is_ancestor(one_up_parent, ancestor_key_name)

    def add_hook(self, key_name, hook_name, hook_dict):
        """Add hook to the keyframe key_name."""
        kf = self.dct[key_name]
        if 'hooks' not in kf:
            kf['hooks'] = {}
        kf['hooks'][str(hook_name)] = hook_dict

    def remove_hook(self, key_name, hook_name):
        """Remove hook from the keyframe key_name."""
        kf = self.dct[key_name]
        if 'hooks' in kf:
            if hook_name in kf['hooks']:
                return kf['hooks'].pop(hook_name)

    def list_hooks(self, key_name):
        """Return list of all hooks attached to key_name."""
        kf = self.dct[key_name]
        if 'hooks' not in kf:
            return []
        else:
            return kf['hooks'].iterkeys()


class Channel(object):

    """Arbitrary waveform channel.

    Holds all information to create an arbitrary waveform channel. Each channel
    has the following attributes:

    ch_name(str) - name of the channel
    key_frame_list(KeyFrameList) - key frames to use for timing information.
    dct(dict) - all channel data is here.

    dct has the following structure:
    {
        "comment": "info about the channel.",
        "id": "indentifier of the physical hardware channel.",
        "type": "analog", # (or "digital")
        "keys": {
            # set of keyframes for which channel info is provided
            "key_name_1":{
                "ramp_type": "linear",
                "ramp_data": {
                    "value": 1.0,
                    ...
                }
                "state": True # only for digital channels
            .
            .
            .
            }
        }
    }

    A ramp is defined by its value at certain keyframes and the kind of
    interpolation between keyframes. The "keys" dict has all the keys for which
    the ramp value is defined. At each keyframe, ramp_data has all the channel
    information between that key and the next key.
    """

    def __init__(self, ch_name, dct=None, key_frame_list=None):
        if dct is None:
            return
        self.ch_name = ch_name
        self.dct = dct
        self.key_frame_list = key_frame_list

    def set_name(self, new_ch_name):
        """Sets the name of the channel."""
        self.ch_name = new_ch_name

    def generate_ramp(self, time_div=4e-3):
        """Returns the generated ramp and a time array.

        This function assumes a uniform time division throughout.

        time_div - time resolution of the ramp.
        """
        if self.dct['type'] == 'analog':
            is_analog = True
        else:
            is_analog = False
        skl = self.key_frame_list.sorted_key_list()
        # each element in used_key_frames is a tuple (key_name, key_dict)
        used_key_frames = []
        for kf in skl:
            if kf in self.dct['keys']:
                used_key_frames.append((kf, self.dct['keys'][kf]))
        max_time = self.key_frame_list.get_absolute_time(skl[-1]) + time_div

        time = np.arange(0.0, max_time, time_div)
        if is_analog:
            voltage = np.zeros(time.shape, dtype=float)
        else:
            voltage = np.zeros(time.shape, dtype=int)
        kf_times = np.array([self.key_frame_list.get_absolute_time(ukf[0])
                             for ukf in used_key_frames])
        kf_positions = kf_times/time_div

        if is_analog:
            # set the start and the end part of the ramp
            start_voltage = used_key_frames[0][1]['ramp_data']['value']
            end_voltage = used_key_frames[-1][1]['ramp_data']['value']
            voltage[0:kf_positions[0]] = start_voltage
            voltage[kf_positions[-1]:] = end_voltage
        else:
            start_voltage = int(used_key_frames[0][1]['state'])
            end_voltage = int(used_key_frames[-1][1]['state'])
            voltage[0:kf_positions[0]] = start_voltage
            voltage[kf_positions[-1]:] = end_voltage

        for i in range(len(kf_times)-1):
            start_time = kf_times[i]
            end_time = kf_times[i+1]
            start_index = kf_positions[i]
            end_index = kf_positions[i+1]
            time_subarray = time[start_index:end_index]
            ramp_type = used_key_frames[i][1]['ramp_type']
            ramp_data = used_key_frames[i][1]['ramp_data']
            if is_analog:
                value_final = used_key_frames[i+1][1]['ramp_data']['value']
            else:
                state = used_key_frames[i][1]['state']

            if is_analog:
                parms_tuple = (ramp_data, start_time, end_time, value_final,
                               time_subarray)
            else:
                parms_tuple = (ramp_data, start_time, end_time, state,
                               time_subarray)

            if is_analog:
                ramp_function = analog_ramp_functions[ramp_type]
            else:
                ramp_function = digital_ramp_functions[ramp_type]
            voltage_sub = ramp_function(*parms_tuple)
            voltage[start_index:end_index] = voltage_sub

        return time, voltage


# Analog Ramp functions


def analog_linear_ramp(ramp_data, start_time, end_time, value_final,
                       time_subarray):
    value_initial = ramp_data["value"]
    interp = (time_subarray - start_time)/(end_time - start_time)
    return value_initial*(1.0 - interp) + value_final*interp


def analog_quadratic_ramp(ramp_data, start_time, end_time, value_final,
                          time_subarray):
    value_initial = ramp_data["value"]
    slope = ramp_data["slope"]
    delta_t = end_time - start_time
    delta_v = value_final - value_initial
    curvature = (delta_v - slope*delta_t)/delta_t**2
    tmt0 = time_subarray - start_time
    return value_initial + slope*tmt0 + curvature*tmt0**2


def analog_quadratic2_ramp(ramp_data, start_time, end_time, value_final,
                           time_subarray):
    value_initial = ramp_data["value"]
    curvature = ramp_data["curvature"]
    delta_t = end_time - start_time
    delta_v = value_final - value_initial
    slope = (delta_v - curvature*delta_t**2)/delta_t
    tmt0 = time_subarray - start_time
    return value_initial + slope*tmt0 + curvature*tmt0**2


def analog_exp_ramp(ramp_data, start_time, end_time, value_final,
                    time_subarray):
    value_initial = ramp_data["value"]
    tau = ramp_data["tau"]
    if tau == 0:
        return analog_jump_ramp(ramp_data, start_time, end_time, value_final,
                                time_subarray)
    delta_t = end_time - start_time
    delta_v = value_final - value_initial
    tmt0 = time_subarray - start_time
    b = delta_v/(np.exp(delta_t/tau) - 1.0)
    a = value_initial - b
    return a + b*np.exp(tmt0/tau)


def analog_sine_ramp(ramp_data, start_time, end_time, value_final,
                     time_subarray):
    delta_t = time_subarray - start_time
    return (ramp_data['value'] +
            ramp_data['amp']*np.sin(2.0*np.pi*ramp_data['freq']*delta_t +
                                    ramp_data['phase']))


def analog_jump_ramp(ramp_data, start_time, end_time, value_final,
                     time_subarray):
    return np.ones(time_subarray.shape)*(ramp_data["value"])


def analog_cubic_ramp(ramp_data, start_time, end_time, value_final,
                      time_subarray):
    return analog_jump_ramp(ramp_data, start_time, end_time, value_final,
                            time_subarray)

# Digital ramp functions start here


def digital_jump_ramp(ramp_data, start_time, end_time, state,
                      time_subarray):
    return np.ones(time_subarray.shape, dtype=int)*int(state)


def digital_pulsetrain_ramp(ramp_data, start_time, end_time, state,
                            time_subarray):
    phase = (time_subarray - start_time)*ramp_data['freq']
    phase += ramp_data['phase']/np.pi/2.0
    duty_cycle = ramp_data['duty_cycle']
    train = np.array((phase % 1.0) < duty_cycle, dtype=int) * int(state)
    return train


analog_ramp_types = {"jump": ["value"],
                     "quadratic": ["value", "slope"],
                     "linear": ["value"],
                     "cubic": ["value", "slope_left", "slope_right"],
                     "sine": ["value", "amp", "freq", "phase"],
                     "quadratic2": ["value", "curvature"],
                     "exp": ["value", "tau"]}

digital_ramp_types = {"jump": [],
                      "pulsetrain": ["freq", "phase", "duty_cycle"]}

analog_ramp_functions = {"jump": analog_jump_ramp,
                         "linear": analog_linear_ramp,
                         "quadratic": analog_quadratic_ramp,
                         "cubic": analog_cubic_ramp,
                         "sine": analog_sine_ramp,
                         "quadratic2": analog_quadratic2_ramp,
                         "exp": analog_exp_ramp}

digital_ramp_functions = {"jump": digital_jump_ramp,
                          "pulsetrain": digital_pulsetrain_ramp}

if __name__ == '__main__':
    with open('examples/test_scene.json', 'r') as f:
        data = json.load(f)
    kfl = KeyFrameList(data['keyframes'])
    channels = [Channel(ch_name, dct, kfl)
                for ch_name, dct in data['channels'].items()]
    ch = channels[0]
