"""6 Channel PPM output to test motor controler"""
"""https://github.com/NiklasFauth/hoverboard-firmware-hack"""

import thread
import logging
import time
import pygame
from pygame import joystick, event, JOYAXISMOTION, JOYHATMOTION
from pygame import JOYBUTTONUP, JOYBUTTONDOWN
import signal

# array index is axis > ppm channel, -1 to skip
# this example, asign joy axis 0 to chanel 0, joy axis 1 to chanel 1 etc. etc.
# AETR presumed x = 0, y = 1, twist = 2, throttle = 3
JOY_AXIES = [1, 2, 0, 3]
# a 5 axis joystick ignoring axis 2 would be as follows
#JOYA = [0, 1, -1, 2, 3]
# a 4 axis joystick swapping axies 0 and 1 would be as follows
#JOYA = [1, 0, 2, 3]
# array index is button > ppm channel, -1 to skip
# this example, asign joy button 0 to chanel 4, joy button 1 to chanel 5 etc. etc.
JOY_BUTTONS = [4, 5,]
JOY_REVERSE = [False, False, False, False, False, False]

try:
    import pigpio
except ImportError as err:
    logging.warn(err, exc_info=True)
    logging.warn("Failed to load pigpio library, running in debug mode")
    pigpio = None

#pigpio = None
RUNNING = False
PI_PPM = 24
PI_GPIO = 1 << PI_PPM

pinst = None
waves = [None, None, None]
channelsglb = [0, 0, 0, 0, 0, 0]
trimglb = [0, 0, 0, 0, 0, 0]

def readjoythread():
    """Read joystick loop and pass result onto processor"""
    global channelsglb, trimglb
    output = [0, 0, 0, 0, 0, 0]
    trim = [0, 0, 0, 0, 0, 0]
    joystick.init()
    joystick.Joystick(0).init()
    time.sleep(1)
    for evt in pygame.event.get():
        time.sleep(.02)

    for i in range(0, len(JOY_AXIES)):
        if JOY_AXIES[i] > -1:
            output[JOY_AXIES[i]] = round(joystick.Joystick(0).get_axis(i), 4)
            if output[JOY_AXIES[i]] is None:
                output[JOY_AXIES[i]] = 0
    for chan in JOY_BUTTONS:
        output[chan] = -1

    channelsglb = output[:]

    while RUNNING:
        haschanged = False
        evt = event.wait()
        if evt.type == JOYAXISMOTION:
            if evt.axis < len(JOY_AXIES) and JOY_AXIES[evt.axis] > -1:
                output[JOY_AXIES[evt.axis]] = round(evt.value, 4)
                haschanged = True
        if evt.type == JOYHATMOTION:
            trim[0] = trim[0] + round((evt.value[0] * .01), 4)
            trim[1] = trim[1] + 0 - (round((evt.value[1] * .01), 4))
            haschanged = True
        elif evt.type == JOYBUTTONUP or evt.type == JOYBUTTONDOWN:
            if evt.button < len(JOY_BUTTONS) and JOY_BUTTONS[evt.button] > -1:
                output[JOY_BUTTONS[evt.button]] = -1 if evt.type == JOYBUTTONUP else 1
                haschanged = True
        if haschanged:
            channelsglb=output[:]
            trimglb=trim[:]

def processoutput():
    """process outout and send wave to pigpio"""
    global pinst, waves, channelsglb, trimglb
    
    while RUNNING:
        channels = channelsglb[:]
        trim = trimglb[:]
        for i in range(0, len(channels)):
            if JOY_REVERSE[i]:
                channels[i] = round(0 - (channels[i] + trim[i]),4)
            else:
                channels[i] = round(channels[i] + trim[i],4)

        if pigpio:
            pulses, pos = [], 0
            for value in channels:
                # calibrated with Taranis to [-99.6..0..99.4]
                uss = int(round(1500 + 453 * value))
                pulses += [pigpio.pulse(0, PI_GPIO, 300),
                        pigpio.pulse(PI_GPIO, 0, uss - 300)]
                pos += uss

            pulses += [pigpio.pulse(0, PI_GPIO, 300),
                    pigpio.pulse(PI_GPIO, 0, 20000 - 300 - pos - 1)]

            pinst.wave_add_generic(pulses)
            waves.append(pinst.wave_create())
            pinst.wave_send_using_mode(waves[-1], pigpio.WAVE_MODE_REPEAT_SYNC)

            last, waves = waves[0], waves[1:]
            if last:
                pinst.wave_delete(last)
        else:
            outputchan = []
            for value in channels:
                # calibrated with Taranis to [-99.6..0..99.4]
                uss = int(round(1500 + 453 * value))
                outputchan.append(uss)
            logging.warn(channels)
            logging.warn(outputchan)
        time.sleep(.02)

def shutdown(signum, frame):
    global RUNNING
    RUNNING = False

def main():
    """Main Entry point"""
    global pinst, waves
    if pigpio:
        pinst = pigpio.pi()
        pinst.set_mode(PI_PPM, pigpio.OUTPUT)
        pinst.wave_add_generic([pigpio.pulse(PI_GPIO, 0, 2000)])
        # padding to make deleting logic easier
        waves = [None, None, pinst.wave_create()]
        pinst.wave_send_repeat(waves[-1])

    pygame.init()
    thread.start_new_thread(readjoythread, ())
    thread.start_new_thread(processoutput, ())
    while RUNNING:
        time.sleep(.02)

    pygame.quit()

if __name__ == '__main__':
    RUNNING = True
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    main()
