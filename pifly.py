from pygame import joystick, event
from pygame import QUIT, JOYAXISMOTION, JOYBALLMOTION, JOYHATMOTION, JOYBUTTONUP, JOYBUTTONDOWN
import pygame
import thread
import time
import logging 

try:
    import pigpio
except ImportError as e:
    logging.warn(e, exc_info=True)
    logging.warn("Failed to load pigpio library, running in debug mode")
    pigpio = None

_pi = None
_waves = [None,None,None]
_running = False
_pi_gpio = 1 << 24
_joyA = [0,1,2,3]
_joyB = [4,5,6,7]

def readjoythread():
    output = [0,0,0,0,0,0,0,0]
    
    joystick.init()
    joystick.Joystick(0).init()
    for evt in pygame.event.get():
        time.sleep(.02)

    for x in range(0, len(_joyA)):
        if _joyA[x] >-1:
            output[_joyA[x]] = round(joystick.Joystick(0).get_axis(x),4)
            if output[_joyA[x]] == None:
                output[_joyA[x]] = 0
    for chan in _joyB:
        output[chan] = -1
    
    processoutput(output[:])

    while _running:
        haschanged = False
        e = event.wait();  
        if e.type == JOYAXISMOTION: 
            if e.axis < len(_joyA) and _joyA[e.axis] > -1:
                 haschanged = True
                 output[_joyA[e.axis]] = round(e.value,4)
        elif e.type == JOYBUTTONUP: 
            if e.button < len(_joyB) and _joyB[e.button] > -1:
                 output[_joyB[e.button]] = -1
                 haschanged = True
        elif e.type == JOYBUTTONDOWN: 
            if e.button < len(_joyB) and _joyB[e.button] > -1:
                 output[_joyB[e.button]] = 1
                 haschanged = True
        if haschanged:
            processoutput(output[:])

def processoutput(channels):
    if pigpio:
        pulses, pos = [], 0
        for value in channels:
            # calibrated with Taranis to [-99.6..0..99.4]
            us = int(round(1333 + 453 * value))
            pulses += [pigpio.pulse(0, _pi_gpio, 300),
                       pigpio.pulse(_pi_gpio, 0, us - 300)]
            pos += us

            pulses += [pigpio.pulse(0, _pi_gpio, 300),
                       pigpio.pulse(_pi_gpio, 0, 20000 - 300 - pos - 1)]

            _pi.wave_add_generic(pulses)
            _waves.append(_pi.wave_create())
            _pi.wave_send_using_mode(waves[-1], pigpio.WAVE_MODE_REPEAT_SYNC)

            last, waves = waves[0], waves[1:]
            if last:
                _pi.wave_delete(last)
    else :
        logging.warn(channels)
    

def main():
    global _pi, _waves
    if pigpio:
        _pi = pigpio.pi('test')
        _pi.set_mode(PPM_OUTPUT_PIN, pigpio.OUTPUT)
        _pi.wave_add_generic([pigpio.pulse(pi_gpio, 0, 2000)])
        # padding to make deleting logic easier
        _waves = [None, None, _pi.wave_create()]
        _pi.wave_send_repeat(waves[-1])

    pygame.init()
    thread.start_new_thread(readjoythread, ())
    while _running:
        time.sleep(.02)

if __name__ == '__main__':
    _running = True
    #signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    main()
