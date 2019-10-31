#RPi.GPIO in Windows
if __name__ != '__main__':
    BCM = 11
    BOARD = 10
    BOTH = 33
    FALLING = 32
    HARD_PWM = 43
    HIGH = 1
    I2C = 42
    IN = 1
    LOW = 0
    OUT = 0
    PUD_DOWN = 21
    PUD_OFF = 20
    PUD_UP = 22
    RISING = 31
    RPI_INFO = {}
    SERIAL = 40
    SPI = 41
    UNKNOWN = -1
    VERSION = "0.6.5"

    def add_event_callback():
        pass
    def add_event_detect ():
        pass
    def cleanup ():
        pass
    def event_detected():
        pass
    def getmode (): #获取编号方式
        pass
    def gpio_function ():
        pass
    def input ():
        pass
    def output ():
        pass
    def remove_event_detect ():
        pass
    def setmode ():
        pass
    def setup ():
        pass
    def setwarnings ():
        pass
    def wait_for_edge ():
        pass

    class PWM (object):
        def ChangeDutyCycle(self):
            pass
        def ChangeFrequency(self):
            pass
        def mro (self):
            pass
        def start (self):
            pass
        def stop (self):
            pass 

