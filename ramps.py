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
        for key in dct:
            print(key)


if __name__ == '__main__':
    with open('examples/test_scene.json', 'r') as f:
        data = json.load(f)
    kfl = KeyFrameList(data['keyframes'])
