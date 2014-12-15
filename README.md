# rampage

A PyQt4 application to generate arbitrary waveforms.

A ramp is stored as a .json file and consists of
    - keyframes
    - channels
    - hooks

## keyframes
Keyframes are positions in time defined with respect to other frames. Every keyframe has the following properties:

- **name**(_string_) - uniquely identifies a keyframe. Two keyframes cannot have the same name
- **comment**(_string_) - brief description of the keyframe.
- **parent**(_string_ or _null_) - name of the parent keyframe. The time position of the keyframe is with respect to the time of the parent. If parent is null then time is taken to be the absolute time.
- **time**(_float_) - The position in time of the keyframe with respect to its parent. Time can be negative, which means that the keyframe is placed before its parent on the time axis.


## channels

parms tuple

parms(0) ramp_data
parms(1) t_initial
parms(2) t_final
parms(3) value_final
prams(4) time_array
