#! /usr/bin/python2
import sys

sys.path.append('Adafruit_Python_DHT')
sys.path.append('hx711py')
import time
import sys
import Adafruit_DHT
import httplib
import urllib
import time
from decimal import *

###########User variables ############
intervall = 60  # sending intervall in sec default: 300
printOn = True  # default False, use True for debugging
beekeeper_active = False  # flag set on, when weight change from last period above threashold
threashold_weight = 1  # in kg
MAX_Length = 30  # how many measurements is a beekeeper active
getcontext().prec = 5  # rounding of weight
record = list()  # store of weight


sensor = Adafruit_DHT.DHT11
pin = 4  # Pin on Raspi
EMULATE_HX711 = False
referenceUnit = 15.285  # determined during first tare

if not EMULATE_HX711:
    import RPi.GPIO as GPIO
    from hx711 import HX711
else:
    from emulated_hx711 import HX711


def send():
    while True:
        params = urllib.urlencode(
            {'field1': weight, 'field2': temperature, 'field3': humidity, 'field4': beekeeper_active, 'field5': offset,
             'key': key})
        headers = {"Content-typZZe": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = httplib.HTTPConnection("api.thingspeak.com:80")
        try:
            conn.request("POST", "/update", params, headers)
            response = conn.getresponse()
            if (printOn):
                print(params)
                print(response.status, response.reason)
            data = response.read()
            conn.close()
            break
        except:
            # print "connection failed"
            return


def cleanAndExit():
    if (printOn):
        print("Cleaning...")
    if not EMULATE_HX711:
        GPIO.cleanup()
    if (printOn):
        print("Bye!")
    sys.exit()


def get_offset():
    f = open("offset.txt", "r")
    return Decimal(f.read())

def set_offset(offset):
    with open('offset.txt', 'w') as f:
        f.write(str(offset))
    f.close()

def get_key():
    f = open("key.txt", "r")
    return f.read().rstrip()

key = get_key()
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(referenceUnit)
hx.reset()
hx.tare()
offset = get_offset()
if (printOn):
    print("Tare done! Add weight now...")

while True:
    try:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

        raw = hx.get_weight(5) / 1000
        curr_weight = Decimal(raw) * 1
        if (len(record) >= MAX_Length):
            if (abs(curr_weight - record[MAX_Length - 1]) > threashold_weight and beekeeper_active == False):
                beekeeper_active = True
                active_periods = 0
                curr_weight = record[MAX_Length - 1]
            if (beekeeper_active == True):
                if (active_periods < MAX_Length):
                    active_periods = active_periods + 1
                    curr_weight = record[MAX_Length - 1]
                else:
                    beekeeper_active = False
                    net_change = curr_weight - record[0]
                    offset = offset - net_change
            del record[0]
        record.append(curr_weight)
        weight = curr_weight + offset

        send()
        set_offset(weight)
        hx.power_down()
        hx.power_up()
        time.sleep(intervall)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()
