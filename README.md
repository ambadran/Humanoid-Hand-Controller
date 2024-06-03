# Humanoid-Hand-Controller

Interfacing muscle sensor V2 using micropython code 

(OPTIONAL BUT RECOMMENDED: Use AD7705 16-bit ADC to give more resolution and muscle activity range to play with)

The idea is to program a sequence of muscle intensities at specific time intervals which correlate to a specific `Movmement` python object

This `Movement` object can then be mapped to any actual transducer action you like. 

In this library it is assumed that the transducer is 5 servo motors each controlling a finger.
