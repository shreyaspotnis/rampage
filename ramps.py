"""Provides classes to build arbitrary waveforms."""
import json


class KeyFrame(object):
    """Basic timing element.

    A keyframe is a position in time relative to another keyframe which is its
    parent. If the keyframe does not have a parent, then the time is relative
    to t=0, which is the start of the scene.

    The name of the keyframe uniquely identifies it, so name clashes are not
    allowed."""

    def __init__(self, name="newkey", time=0.0, parent=None, comment=""):
        """__init__(self, name='keyframe', time=0.0, parent=None, comment="")

        Initialize a keyframe.

        name : string
            Identifier for the keyframe
        time : float
            Time relative to the parent. If parent is None, then it
            is the absolute time. relative time can be negative, but absolute
            time is always positive.
        parent : KeyFrame
            Time is measured relative to the time of parent. If parent is None,
            then time is absolute
        comment : string
            More information about the keyframe
        """

        self.set_name(name)
        self.set_parent(parent)
        self.set_time(time)
        self.set_comment(comment)

    def set_name(self, new_name):
        self.name = new_name

    def set_parent(self, new_parent):
        self.parent = new_parent

    def set_time(self, new_time):
        self.time = new_time

    def set_comment(self, new_comment):
        self.comment = new_comment


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
        abs_times = [self.get_absolute_time(key) for key in self.dct]
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


if __name__ == '__main__':
    with open('examples/test_scene.json', 'r') as f:
        data = json.load(f)
    kfl = KeyFrameList(data['keyframes'])
