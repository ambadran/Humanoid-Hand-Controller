from muscle_sensor import read_contraction_and_execute, muscle, ad
from machine import Pin, Timer
import time
from micropython import const

FIRST_COMMAND_DELAY_TIME = const(300)
SECOND_COMMAND_DELAY_TIME = const(1000)
THIRD_COMMAND_DELAY_TIME = const(2000)

def main():
    '''
    Main Routine
    '''
    # BUTTON IS ACTIVE LOW
    button = Pin(22, Pin.IN, Pin.PULL_DOWN)
    button_pressed = False
    led = Pin(25, Pin.OUT)

    timer = Timer(period=500, mode=Timer.PERIODIC, callback=lambda t:led.value(not led.value()))

    try:
        while True:
            while not button.value():
                if not button_pressed:
                    start = time.ticks_ms()
                    button_pressed = True

            if button_pressed:
                if time.ticks_diff(time.ticks_ms(), start) <= FIRST_COMMAND_DELAY_TIME:
                    read_contraction_and_execute()

                elif time.ticks_diff(time.ticks_ms(), start) <= SECOND_COMMAND_DELAY_TIME:
                    muscle.calibrate_muscle_intensity_ranges()

                # elif time.ticks_diff(time.ticks_ms(), start) <= THIRD_COMMAND_DELAY_TIME:
                else:  ## until I want to add another command
                    muscle.test_ad(5)  # persistently print ad values for 5 seconds

                #TODO: make a default screen to appear after each function
                # MuscleSensorStatus.report_saved_movements(hum)

                button_pressed = False

    except Exception as e:
        print("Error: ", e)

    finally:
        timer.deinit()
        led.off()



main()
