# Write your code here :-)
from machine import Pin, Time, TouchPad
pint = Pin(2,PinOUT)
touchie = TouchPad(Pin(4))
while True:
    reader =touchie.read()
    if (reader<300)
        pint.value(1)
        time.sleep(0.5)
