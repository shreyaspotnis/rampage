"""Provides classes to build arbitrary waveforms."""

import json


class KeyFrameList(object):

    """Basic timing element.

    Holds a list of keyframes. Each keyframe is a position in time relative to
    a parent keyframe. If parent keyframe is None, then the time is relative
    to the start of the ramp."""

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
        """Find absolute times for all keys."""
        for key in self.dct:
            self.get_absolute_time(key)
        self.is_baked = True

    def unbake(self):
        """Remove absolute times for all keys."""
        for key in self.dct:
            self.dct[key].pop('__abs_time__', None)
        self.is_baked = False

    def get_absolute_time(self, key):
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

    def set_time(self, key, new_time):
        """Sets the time of key."""
        self.unbake()
        kf = self.dct[key]
        kf['time'] = new_time
        self.bake()

    def set_comment(self, key, new_comment):
        """Sets the comment of key."""
        kf = self.dct[key]
        kf['comment'] = new_comment

    def set_parent(self, key, new_parent):
        """Sets the parent of the key."""
        self.unbake()
        kf = self.dct[key]
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

    def add_keyframe(self, new_key, new_key_dict):
        self.unbake()
        self.dct[new_key] = new_key_dict
        self.bake()

    def del_keyframe(self, key):
        self.unbake()
        kf = self.dct[key]
        parent_key = kf['parent']

        # find children of this keyframe
        child_keys = [k for k in self.dct if self.dct[k]['parent'] == key]
        # set the parent of child keys to the parent of the deleted key
        for ck in child_keys:
            self.dct[ck]['parent'] = parent_key
        # remove the key
        self.dct.pop(key)
        self.bake()

    def is_ancestor(self, child_key, ancestor_key):
        """Returns True if ancestor lies in the ancestry tree of child."""

        # all keys are descendents of None
        if ancestor_key is None:
            return True

        one_up_parent = self.dct[child_key]['parent']
        if child_key == ancestor_key:
            # debatable semantics, but a person lies in his/her own
            # ancestry tree
            return True
        elif one_up_parent is None:
            return False
        else:
            return self.is_ancestor(one_up_parent, ancestor_key)


ramp_types = {
    "jump": ["value"],
    "linear": ["value"],
    "quadratic": ["value", "slope"],
    "cubic": ["value", "slope_left", "slope_right"],
}


class Channel(object):

    """Arbitrary waveform channel."""

    def __init__(self, ch_name, dct=None, key_frame_list=None):
        if dct is None:
            return
        self.ch_name = ch_name
        self.dct = dct
        self.key_frame_list = key_frame_list
        # fill in all entries that are left blank
        print(self.key_frame_list)
        # for key in self.key_frame_list.dct:
        #     if not key in self.dct:
        #         self.dct[key] = {}

    def set_name(self, new_ch_name):
        self.ch_name = new_ch_name


if __name__ == '__main__':
    with open('examples/test_scene.json', 'r') as f:
        data = json.load(f)
    kfl = KeyFrameList(data['keyframes'])
    channels = [Channel(ch_name, dct, kfl)
                for ch_name, dct in data['channels'].items()]
    ch = channels[0]
