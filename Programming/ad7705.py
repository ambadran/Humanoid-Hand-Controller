from machine import Pin, SoftSPI
from micropython import const
from time import sleep_ms

REG_CMM = const(0x0) #communication register 8 bit
REG_SETUP = const(0x1) #setup register 8 bit
REG_CLOCK = const(0x2) #clock register 8 bit
REG_DATA = const(0x3) #data register 16 bit, contains conversion result
REG_TEST = const(0x4) #test register 8 bit, POR 0x0
REG_NOP = const(0x5) #no operation
REG_OFFSET = const(0x6) #offset register 24 bit
REG_GAIN = const(0x7) # gain register 24 bit

#channel selection for AD7706 (for AD7705 use the first two channel definitions)
#CH1 CH0
CHN_AIN1 = const(0x0) #AIN1; calibration register pair 0
CHN_AIN2 = const(0x1) #AIN2; calibration register pair 1
CHN_COMM = const(0x2) #common; calibration register pair 0
CHN_AIN3 = const(0x3) #AIN3; calibration register pair 2

#output update rate
#CLK FS1 FS0
UPDATE_RATE_20 = const(0x0) # 20 Hz
UPDATE_RATE_25 = const(0x1) # 25 Hz
UPDATE_RATE_100 = const(0x2) # 100 Hz
UPDATE_RATE_200 = const(0x3) # 200 Hz
UPDATE_RATE_50 = const(0x4) # 50 Hz
UPDATE_RATE_60 = const(0x5) # 60 Hz
UPDATE_RATE_250 = const(0x6) # 250 Hz
UPDATE_RATE_500 = const(0x7) # 500 Hz

#operating mode options
#MD1 MD0
MODE_NORMAL = const(0x0) #normal mode
MODE_SELF_CAL = const(0x1) #self-calibration
MODE_ZERO_SCALE_CAL = const(0x2) #zero-scale system calibration, POR 0x1F4000, set FSYNC high before calibration, FSYNC low after calibration
MODE_FULL_SCALE_CAL = const(0x3) #full-scale system calibration, POR 0x5761AB, set FSYNC high before calibration, FSYNC low after calibration

#gain setting
GAIN_1 = const(0x0)
GAIN_2 = const(0x1)
GAIN_4 = const(0x2)
GAIN_8 = const(0x3)
GAIN_16 = const(0x4)
GAIN_32 = const(0x5)
GAIN_64 = const(0x6)
GAIN_128 = const(0x7)

UNIPOLAR = const(0x0)
BIPOLAR = const(0x1)

CLK_DIV_1 = const(0x1)
CLK_DIV_2 = const(0x2)

MODE = const(0b11) #SPI_CPHA | SPI_CPOL
BITS = const(8)
SPEED = const(50000)
DELAY = const(10)

DEFAULT_VREF = const(3.3)

class AD770X():
    def __init__(self) :        
        # RP2040 zero waveshare board
        # self.spi = SoftSPI(baudrate=SPEED, polarity=1, phase=1, sck=Pin(6), mosi=Pin(7), miso=Pin(4))
        # self.CS = Pin(27, Pin.OUT)

        # raspberry pi pico board
        self.spi = SoftSPI(baudrate=SPEED, polarity=1, phase=1, sck=Pin(6), mosi=Pin(3), miso=Pin(0))
        self.CS = Pin(7, Pin.OUT)

        self.initChannel(CHN_AIN1)

    def initChannel(self, channel,clkDivider=CLK_DIV_1, polarity=BIPOLAR, gain=GAIN_1, updRate=UPDATE_RATE_25):
        self.setNextOperation(REG_CLOCK, channel, 0)
        self.writeClockRegister(0, clkDivider, updRate)

        self.setNextOperation(REG_SETUP, channel, 0)
        self.writeSetupRegister(MODE_SELF_CAL, gain, polarity, 0, 0)

        sleep_ms(300)

    def setNextOperation(self,reg,channel,readWrite) :
        r = reg << 4 | readWrite << 3 | channel
        r = r.to_bytes(1, 'h')
        # print(f"Writing: {r}")  # for Debugging
        self.spi.write(r)

    def writeClockRegister(self, CLKDIS, CLKDIV, outputUpdateRate) :
        '''
        Clock Register
           7      6       5        4        3        2      1      0
        ZERO(0) ZERO(0) ZERO(0) CLKDIS(0) CLKDIV(0) CLK(1) FS1(0) FS0(1)

        CLKDIS: master clock disable bit
        CLKDIV: clock divider bit
        '''
        r = CLKDIS << 4 | CLKDIV << 3 | outputUpdateRate
        r &= ~(1 << 2); # clear CLK
        r = r.to_bytes(1, 'h')
        # print(f"Writing: {r}")  # for Debugging
        self.spi.write(r)

    def writeSetupRegister(self,operationMode,gain,unipolar,buffered,fsync) :
        '''
        Setup Register:
          7     6     5     4     3      2      1      0
        MD10) MD0(0) G2(0) G1(0) G0(0) B/U(0) BUF(0) FSYNC(1)
        '''
        r = operationMode << 6 | gain << 3 | unipolar << 2 | buffered << 1 | fsync
        r = r.to_bytes(1, 'h')
        # print(f"Writing: {r}")  # for Debugging
        self.spi.write(r)

    def readADResult(self) :
        buf = bytearray(2)
        self.spi.readinto(buf, 0x00)

        r = int(buf[0] << 8 | buf[1])
        return r

    def readADResultRaw(self,channel=CHN_AIN1) :
        # while not self.dataReady(channel) :
        #     pass
        self.setNextOperation(REG_DATA, channel, 1)

        return self.readADResult()

    def readVoltage(self, channel=CHN_AIN1, vref=DEFAULT_VREF, factor=1) :    
        return float(self.readADResultRaw(channel)) / 65536.0 * vref * factor

    def keep_reading(self, wanted_func):
        try:
            while True:
                print(f"Reading: {wanted_func()}", end=' \r')
                sleep_ms(100)

        except KeyboardInterrupt:
            return

        
ad = AD770X()

# open repl, `from ad7705 import *` then `ad.keep_reading(ad.readADResultRaw)` to view 16-bit ADC value
