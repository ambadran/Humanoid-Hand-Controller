from ad7705 import ad
import time
from machine import Timer
from servo import Servo


'''
holding tuples values of upper and lower bound

Listed from lowest intensity to highest intensity
'''
class MuscleIntensity:
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
muscle_intensities_bounds = [(0, 9000), (9000, 12000), (12000, 15000), (15000, 40000)]
    
class Movement:
    '''
    A specific muscle movement consists of a specific muscle contractions in a specific order with specific intervals between each muscle contraction. 
    '''
    MAXIMUM_NUM_INTENSITIES = 4
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
    MAXIMUM_DEGREE = 180
    def __init__(self, servo_pin: int, movement: Movement):
        self._servo = Servo(pin_id=servo_pin)
        self.movement = movement

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

class MuscleSensorStatus:
    PENDING_MUSCLE_ACTIVIITY ="PENDING_MUSCLE_ACTIVIITY" 
    READING_ORDER_IN_PROGRESS ="READING_ORDER_IN_PROGRESS" 
    MOVEMENT_DETECTED ="MOVEMENT_DETECTED" 
    MOVEMENT_INVALID ="MOVEMENT_INVALID" 
    IDLE ="IDLE" 

class MuscleSensor:
    '''
    Class to interface EMG Muscle Sensor V3

    the muscle measurements raw values range from 36 hundreds to 45 hundreds
    '''
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

    def read_mucsle_intensity(self) -> MuscleIntensity:
        '''
        reading current AD value and translating it into a muscle intensity range value
        '''
        value = self.ad.readADResultRaw()
        for ind, bound in enumerate(muscle_intensities_bounds):
            if bound[0] <= value <= bound[1]:
                return ind

    def detect_muscle_contraction(self) -> bool:
        self.status = MuscleSensorStatus.PENDING_MUSCLE_ACTIVIITY  #TODO: make while loop internal
        current_value = self.read_mucsle_intensity()
        if not current_value:
            return False

        else:
            self.status = MuscleSensorStatus.READING_ORDER_IN_PROGRESS
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

        self.current_time = 0
        self.muscle_intensities_order = []

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
Finger( 0, Movement(                           
    ( MuscleIntensity.HIGH, MuscleIntensity.MEDIUM, MuscleIntensity.LOW ),
    (         0,                      1,                      3 )) ),

Finger( 1, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.MEDIUM, MuscleIntensity.HIGH ),
    (         0,                      2,                      3         )) ),

Finger( 2, Movement(                           
    ( MuscleIntensity.MEDIUM, MuscleIntensity.MEDIUM, MuscleIntensity.MEDIUM,  MuscleIntensity.MEDIUM),
    (         0,                      1,                      2,                          3)) ),

Finger( 3, Movement(                           
    ( MuscleIntensity.LOW, MuscleIntensity.LOW, MuscleIntensity.LOW,  MuscleIntensity.LOW),
    (         0,                      1,                      2,                          3)) ),

Finger( 5, Movement(                           
    ( MuscleIntensity.HIGH, MuscleIntensity.HIGH, MuscleIntensity.HIGH,  MuscleIntensity.HIGH),
    (         0,                      1,                      2,                          3)) )

))

movements = humanoid_hand.movement_tuple()
print(f"Defined Movements:\n")
for ind, movement in enumerate(movements):
    print(f"Movement{ind+1}: {movement.muscle_intensities_order}")
print('\n')

muscle = MuscleSensor(ad, movements)

def read_contraction_and_execute():
    muscle.detect_muscle_contraction()
    while muscle.status == MuscleSensorStatus.PENDING_MUSCLE_ACTIVIITY:
        muscle.detect_muscle_contraction()
        print(f"{muscle.status}: Muscle Intensity: {muscle.muscle_intensities_order} @ time: {muscle.current_time} ", end=' \r')

    print()

    while muscle.status == MuscleSensorStatus.READING_ORDER_IN_PROGRESS:
        print(f"{muscle.status}: Muscle Intensity: {muscle.muscle_intensities_order} @ time: {muscle.current_time} ", end=' \r')

    print()

    if muscle.status == MuscleSensorStatus.MOVEMENT_DETECTED:
        print(f"{muscle.status}: ", end='')  # printing before the method clears the status
        detected_movement_ind = muscle.get_detected_muscle_movement()
        print(detected_movement_ind)
        humanoid_hand.fingers[detected_movement_ind].contraction_toggle()

    elif muscle.status == MuscleSensorStatus.MOVEMENT_INVALID:
        print(f"{muscle.status}!")


