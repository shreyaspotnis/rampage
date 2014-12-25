"""This module handles running the ramps on the experiment."""


class Hooks(object):

    default_mesgs = {'agilent_turn_fm_on': {'start_freq': 40e6},
                     'agilent_output_off': {},
                     'translation_stage_move_x': {'pos': 0.0},
                     'translation_stage_move_y': {'pos': 1.0}
                     }

    def agilent_turn_fm_on(self, mesg_dict):
        # add code to do the gpib stuff
        pass

    def agilent_output_off(self, mesg_dict):
        pass

    def translation_stage_move_x(self, mesg_dict):
        pass

    def translation_stage_move_y(self, mesg_dict):
        pass
