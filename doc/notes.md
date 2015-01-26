Trying out twisted for client service protocol

Had to install twisted, openssl, zope.interface, service_identity

Meanwhile
The card we have -
PCI 6229 -  Digital card
    has 4 analog 16 bit analog outputs - 833kS/s - thats 1 sample per 1.2us

PCI 6713 - 2x Analog cards



- set max and min values to 10.0 and -10.0
- set view ramp such that you can view and change at the same time


# what's the server supposed to be doing?

the server has two states:
'running' and 'paused'
as long as state is running, make ramps in the queue, upload them and run them. Once the ramp is done, pop them from the queue.
when ramps end, go to 'paused'

when user says start, state goes to 'running' if there are ramps queued

if user says abort, cancels currently running ramp and goes to 'paused'. Does not remove the ramp from the queue.



# issues

when adding and removing channels, some numbers in the GUI change to 0, whereas in the ramp they are fine.
