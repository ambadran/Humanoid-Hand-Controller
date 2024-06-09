from ad7705 import ad
import time
from machine import Timer, Pin, I2C
from servo import Servo
import ssd1306
  

class Movement:
    '''
    A specific muscle movement consists of a specific muscle contractions in a specific order with specific intervals between each muscle contraction. 
    '''
    MAXIMUM_NUM_INTENSITIES = 3
    def __init__(self, muscle_intensities: tuple[MuscleIntensity], times: tuple[int]):
        '''
        muscle_intensities: the values that would be read in `times` periods

        OBVIOUS FACT: the MuscleIntensity at time0 must NEVER BE NONE
        '''
        #TODO: check muscle_intensities and times datatypes
        if len(muscle_intensities) != len(times):
            raise ValueError("number of adc_values given must equal number of times given")

        # moving adc values and times into one list where every value is 
        self.muscle_intensities_order = [0 for _ in range(times[-1]+1)]
        for n in range(len(times)):
            self.muscle_intensities_order[times[n]] = muscle_intensities[n]
        self.muscle_intensities_order = tuple(self.muscle_intensities_order)

class Finger:
    MINIMUM_DEGREE = 0
    MAXIMUM_DEGREE = 120
    def __init__(self, servo_pin: int, movement: Movement):
        self._servo = Servo(pin_id=servo_pin)
        self.movement = movement
        self.contraction_off()

    @property
    def contraction_value(self):
        return self._servo.read()

    @contraction_value.setter
    def contraction_value(self, value):
        self._servo.write(value)

    def contraction_full(self):
        self._servo.write(self.MAXIMUM_DEGREE)

    def contraction_off(self):
        self._servo.write(self.MINIMUM_DEGREE)

    def contraction_toggle(self):
        if self.contraction_value:
            self._servo.write(self.MINIMUM_DEGREE)
        else:
            self._servo.write(self.MAXIMUM_DEGREE)

class HumanoidHand:

    # ssd1306 display
    display = ssd1306.SSD1306_I2C(128, 64, I2C(1, scl=Pin(27), sda=Pin(26)))
 
    def __init__(self, fingers: tuple[Finger]):

        if len(fingers) != 5:
            raise ValueError("finger tuple must be 5 values!")

        self.fingers = fingers
        self.finger1 = fingers[0]
        self.finger2 = fingers[1]
        self.finger3 = fingers[2]
        self.finger4 = fingers[3]
        self.finger5 = fingers[4]

    def movement_tuple(self) -> tuple[Movement]:
        '''
        return tuple of Movement in order of fingers from 1 to 5
        very important for MuscleSensor to detect what finger is it
        '''
        movements = []
        for finger in self.fingers:
            movements.append(finger.movement)
        return movements

    def finger_test(self):
        '''
        tests each individual fingers
        '''
        for finger_ind in range(5):
            MuscleSensorStatus.report_custom(f"Testing finger:{finger_ind}!")
            self.fingers[finger_ind].contraction_toggle()
            time.sleep(1)
            self.fingers[finger_ind].contraction_toggle()
            time.sleep(1)

class MuscleSensorStatus:
    PENDING_ACTIVIITY = "PENDING_ACTIVIITY" 
    READ_IN_PROGRESS =  "READ_IN_PROGRESS" 
    MOVEMENT_DETECTED = "MOVEMENT_DETECTED" 
    MOVEMENT_INVALID =  "MOVEMENT_INVALID" 
    IDLE ="IDLE" 

    @classmethod
    def report_full(cls, muscle: MuscleSensor):
        '''
        prints full report in terminal and on ssd1306 screen
        '''
        print(f"{muscle.status}: Muscle Intensity: {muscle.muscle_intensities_order} @ time: {muscle.current_time} ", end=' \r')
        HumanoidHand.display.fill(0)
        HumanoidHand.display.text(muscle.status, 0, 0, 1)
        HumanoidHand.display.text(str(muscle.muscle_intensities_order), 0, 12, 1)
        HumanoidHand.display.text(f"time: {muscle.current_time}", 0, 24, 1)
        HumanoidHand.display.show()

        time.sleep_us(100)

    @classmethod
    def report_status(cls, muscle: MuscleSensor):
        '''
        print status in terminal and ssd1306
        '''
        print(muscle.status)
        HumanoidHand.display.text(muscle.status, 0, 0, 1)
        HumanoidHand.display.show()
        time.sleep_us(100)

    @classmethod
    def report_saved_movements(cls, movements: list[Movement]):
        '''
        prints the saved movements on the screen
        '''
        print(f"Defined Moves:")  # unfortionately can't display this and the 5 movement in the oled screen at once :(
        for ind, movement in enumerate(movements):
            MuscleSensorStatus.report_custom(f"M{ind+1}: {movement.muscle_intensities_order}", clear_display=False, line=ind*12)

    @classmethod
    def report_ad(cls):
        '''
        prints in terminal and ssd1306 the ad values
        '''
        global ad
        ad_value = ad.readADResultRaw()
        print(f"Reading: {ad_value}", end=' \r')
        HumanoidHand.display.fill(0)
        HumanoidHand.display.text(f"AD7705: {ad_value}", 0, 0, 1)
        HumanoidHand.display.show()
        time.sleep_us(100)

    @classmethod
    def report_custom(cls, string, clear_display:bool=True, clear_line: bool=False, line: int=0, ending: str='\n'):
        '''
        display custome message in oled and terminal
        AFTER deleting the whole screen
        '''
        print(string, end=ending)

        if clear_display:
            HumanoidHand.display.fill(0)
        if clear_line:
            # very useful to simulate '\r' like functionality in terminal
            HumanoidHand.display.fill_rect(72, line, 127, 20, 0)

        #TODO: write an algorithm to split text into words then print the most words possible
        #       in the 16 character wide space per line available
        HumanoidHand.display.text(string, 0, line, 1)
        HumanoidHand.display.show()
        time.sleep_us(100)


'''
holding tuples values of upper and lower bound

Listed from lowest intensity to highest intensity
'''
class MuscleIntensity:
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
 
class MuscleSensor:
    '''
    Class to interface EMG Muscle Sensor V3

    the muscle measurements raw values range from 36 hundreds to 45 hundreds
    '''
    muscle_intensities_bounds = [(0, 1000), (1000, 8000), (8000, 10000), (10000, 40000)]
    MAXIMUM_SAMINGLING_TIME = const(1000)  # maximum muscle intensity change period is 1000ms
    def __init__(self, ad, movements: list[Movement]):
        self.ad = ad  # the AD7705 object

        # hashing the movement lists to efficiently match later ;)
        self.muscle_movement_hashes = {}
        for ind, movement in enumerate(movements):
            self.muscle_movement_hashes[movement.muscle_intensities_order] = ind

        # helper variables to identify the muscle_intensities order
        self.current_time = 0
        self.muscle_intensities_order: list[MuscleIntensity] = []  # list of muscle intensities detected
        self.__detected_movement_ind = None
        self.status: MuscleSensorStatus = MuscleSensorStatus.IDLE

    def test_ad(self, seconds):
        '''
        prints ad values persistently for 'seconds' time
        '''
        for _ in range(seconds*10):
            MuscleSensorStatus.report_ad()
            time.sleep_ms(100)

    def calibrate_muscle_intensity_ranges(self):
        '''
        calibration sequence:
        1- ask user to relax for 3 seconds
        2- ask user to do maximum muscle contraction
        3- repeat 1 & 2 three times
        '''
        CALIBRATION_TIMES = 3

        relaxed_intensities = []
        contracted_intensities = []
        dummy_contracted_intensities = []  # the maximum contraction happens for a few ms so the values must be filtered before adding them to the original list

        for _ in range(CALIBRATION_TIMES):
            MuscleSensorStatus.report_custom("Relax Muscle!")
            time.sleep(1)
            deadline = time.ticks_add(time.ticks_ms(), 1000)
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                value = ad.readADResultRaw()
                MuscleSensorStatus.report_custom(f"Reading: {value}", clear_display=False, clear_line=True, line=12, ending=' \r')
                relaxed_intensities.append(value)
            MuscleSensorStatus.report_custom(f"Avg Relax: {sum(relaxed_intensities)/len(relaxed_intensities)}", clear_display=False, line=24, ending='\n\n')
            time.sleep(1)


            MuscleSensorStatus.report_custom("Contract Muscle!")
            time.sleep(1)
            deadline = time.ticks_add(time.ticks_ms(), 1000)
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                value = ad.readADResultRaw()
                MuscleSensorStatus.report_custom(f"Reading: {value}", clear_display=False, clear_line=True, line=12, ending=' \r')
                dummy_contracted_intensities.append(value)
            contracted_intensities.append(max(dummy_contracted_intensities))
            MuscleSensorStatus.report_custom(f"Maximum: {contracted_intensities[-1]}", clear_display=False, line=24, ending='\n\n')
            time.sleep(1)

        relaxed_value = int(sum(relaxed_intensities) / len(relaxed_intensities))
        contracted_value = int(sum(contracted_intensities) / len(contracted_intensities))

        MuscleSensorStatus.report_custom(f"Avg Relaxed:")
        MuscleSensorStatus.report_custom(f"{relaxed_value}", clear_display=False, line=12)
        MuscleSensorStatus.report_custom(f"Avg Contracted:", clear_display=False, line=24)
        MuscleSensorStatus.report_custom(f"{contracted_value}", ending='\n\n', clear_display=False, line=36)

        divisions = contracted_value//10
        v1 = relaxed_value + divisions*1
        v2 = relaxed_value + divisions*4
        v3 = relaxed_value + divisions*6
        v4 = relaxed_value + divisions*10
        self.muscle_intensities_bounds = [(0, v1), (v1, v2), (v2, v3), (v3, v4)]

    def read_mucsle_intensity(self) -> MuscleIntensity:
        '''
        reading current AD value and translating it into a muscle intensity range value
        '''
        value = self.ad.readADResultRaw()
        for ind, bound in enumerate(self.muscle_intensities_bounds):
            if bound[0] <= value <= bound[1]:
                return ind

    def detect_muscle_contraction(self) -> bool:
        self.status = MuscleSensorStatus.PENDING_ACTIVIITY  #TODO: make while loop internal
        current_value = self.read_mucsle_intensity()
        if not current_value:
            return False

        else:
            self.status = MuscleSensorStatus.READ_IN_PROGRESS
            self.muscle_intensities_order = []  # I moved to be cleared with every start (not every end) so that I can see the pattern detected at the end
            self.muscle_intensities_order.append(current_value)
            self.timer = Timer(period=MuscleSensor.MAXIMUM_SAMINGLING_TIME, mode=Timer.PERIODIC, callback=self.read_contraction_order)
            return True

    def read_contraction_order(self, x):
        '''
        :param x: redundant variable for Timer class 
        parsing different movement patterns 
        '''
        self.muscle_intensities_order.append(self.read_mucsle_intensity())
        self.current_time += MuscleSensor.MAXIMUM_SAMINGLING_TIME

        if len(self.muscle_intensities_order) == Movement.MAXIMUM_NUM_INTENSITIES:

            self.timer.deinit()

            self.__detected_movement_ind = self.match_detected_muscle_intensities_order()
            if self.__detected_movement_ind != None:
                self.status = MuscleSensorStatus.MOVEMENT_DETECTED
            else:
                self.status = MuscleSensorStatus.MOVEMENT_INVALID

    def match_detected_muscle_intensities_order(self):
        '''
        matches the newly found muscle_intensities list with the muscle intensity values we have
        And resets the variables
        '''
        movement: Movement = self.muscle_movement_hashes.get(tuple(self.muscle_intensities_order), None)

        self.last_muscle_intensities_order = self.muscle_intensities_order
        # self.muscle_intensities_order = [] // I moved to be cleared with every start (not every end) so that I can see the pattern detected at the end
        self.current_time = 0

        return movement
            
    def get_detected_muscle_movement(self):
        '''
        executes
        '''
        detected_movement_ind = self.__detected_movement_ind
        self.__detected_movement_ind = None
        self.status = MuscleSensorStatus.IDLE

        return detected_movement_ind


humanoid_hand = HumanoidHand((
# Finger( 0, Movement(                           
Finger( 16, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.NONE, MuscleIntensity.NONE ),
    (         0,                      1,                      2 )) ),

# Finger( 1, Movement(                           
Finger( 17, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.LOW, MuscleIntensity.NONE ),
    (         0,                      1,                      2)) ),

# Finger( 2, Movement(                           
Finger( 19, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.NONE, MuscleIntensity.LOW),
    (         0,                      1,                      2)) ),

# Finger( 3, Movement(                           
Finger( 18, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.LOW, MuscleIntensity.LOW),
    (         0,                      1,                      2)) ),

# Finger( 5, Movement(                           
Finger( 20, Movement(                           
    ( MuscleIntensity.MEDIUM, MuscleIntensity.NONE, MuscleIntensity.NONE),
    (         0,                      1,                      2)) )

))

movements = humanoid_hand.movement_tuple()
MuscleSensorStatus.report_saved_movements(movements)

print('\n')

muscle = MuscleSensor(ad, movements)

def read_contraction_and_execute():
    muscle.detect_muscle_contraction()
    while muscle.status == MuscleSensorStatus.PENDING_ACTIVIITY:
        muscle.detect_muscle_contraction()
        MuscleSensorStatus.report_full(muscle)

    print()

    while muscle.status == MuscleSensorStatus.READ_IN_PROGRESS:
        MuscleSensorStatus.report_full(muscle)

    # MuscleSensorStatus.report_full(muscle)
    print()

    if muscle.status == MuscleSensorStatus.MOVEMENT_DETECTED:
        MuscleSensorStatus.report_status(muscle)

        detected_movement_ind = muscle.get_detected_muscle_movement()

        MuscleSensorStatus.report_custom(f"Index: {detected_movement_ind}", clear_display=False, line=36)

        humanoid_hand.fingers[detected_movement_ind].contraction_toggle()

    elif muscle.status == MuscleSensorStatus.MOVEMENT_INVALID:
        MuscleSensorStatus.report_status(muscle)

