from muscle_sensor import read_contraction_and_execute, muscle, ad
from machine import Pin
import time
from micropython import const

FIRST_COMMAND_DELAY_TIME = const(300)
# SECOND_COMMAND_DELAY_TIME = const()

def main():
    '''
    Main Routine
    '''
    # BUTTON IS ACTIVE LOW
    button = Pin(22, Pin.IN, Pin.PULL_DOWN)
    button_pressed = False
    while True:
        while not button.value():
            if not button_pressed:
                start = time.ticks_ms()
                button_pressed = True

        if button_pressed:
            if time.ticks_diff(time.ticks_ms(), start) <= FIRST_COMMAND_DELAY_TIME:
                read_contraction_and_execute()

            # elif time.ticks_diff(time.ticks_ms(), start) <= SECOND_COMMAND_DELAY_TIME:
            else:  ## until I want to add another command
                muscle.calibrate_muscle_intensity_ranges()

            button_pressed = False



            
