"""py joy  fly stick"""
import thread
import logging
import time
import pygame
from pygame import joystick, event, JOYAXISMOTION
from pygame import JOYBUTTONUP, JOYBUTTONDOWN

try:
    import pigpio
except ImportError as err:
    logging.warn(err, exc_info=True)
    logging.warn("Failed to load pigpio library, running in debug mode")
    pigpio = None

RUNNING = False
PI_PPM = 24
PI_GPIO = 1 << PI_PPM

pinst = None
waves = [None, None, None]

# array index is axis > ppm channel, -1 to skip
# this example, asign joy axis 0 to chanel 0, joy axis 1 to chanel 1 etc. etc.
# AETR presumed x = 0, y = 1, twist = 2, throttle = 3
JOYA = [0, 1, 3, 2]
# a 5 axis joystick ignoring axis 2 would be as follows
#JOYA = [0, 1, -1, 2, 3]
# a 4 axis joystick swapping axies 0 and 1 would be as follows
#JOYA = [1, 0, 2, 3]


# array index is button > ppm channel, -1 to skip
# this example, asign joy button 0 to chanel 4, joy button 1 to chanel 5 etc. etc.
JOYB = [4, 5, 6, 7]
def readjoythread():
    """Read joystick loop and pass result onto processor"""
    output = [0, 0, 0, 0, 0, 0, 0, 0]
    joystick.init()
    joystick.Joystick(0).init()
    for evt in pygame.event.get():
        time.sleep(.02)

    for i in range(0, len(JOYA)):
        if JOYA[i] > -1:
            output[JOYA[i]] = round(joystick.Joystick(0).get_axis(i), 4)
            if output[JOYA[i]] is None:
                output[JOYA[i]] = 0
    for chan in JOYB:
        output[chan] = -1

    processoutput(output[:])

    while RUNNING:
        haschanged = False
        evt = event.wait()
        if evt.type == JOYAXISMOTION:
            if evt.axis < len(JOYA) and JOYA[evt.axis] > -1:
                output[JOYA[evt.axis]] = round(evt.value, 4)
                haschanged = True
        elif evt.type == JOYBUTTONUP or evt.type == JOYBUTTONDOWN:
            if evt.button < len(JOYB) and JOYB[evt.button] > -1:
                output[JOYB[evt.button]] = -1 if evt.type == JOYBUTTONUP else 1
                haschanged = True
        if haschanged:
            processoutput(output[:])

def processoutput(channels):
    """process outout and send wave to pigpio"""
    global pinst, waves
    if pigpio:
        pulses, pos = [], 0
        for value in channels:
            # calibrated with Taranis to [-99.6..0..99.4]
            uss = int(round(1333 + 453 * value))
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
        logging.warn(channels)

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
    while RUNNING:
        time.sleep(.02)

    pygame.quit()

if __name__ == '__main__':
    RUNNING = True
    #signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    main()
