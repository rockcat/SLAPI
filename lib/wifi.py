import time
import network
from machine import Pin

wlan= network.WLAN(network.STA_IF)
led = Pin("LED", Pin.OUT)

def reset_connection():
    global wlan 
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)

def connect_wifi(ssid, password, max_wait=0):

    global wlan
    wait = max_wait
    reset_connection()
    
    print('Connecting to network...', ssid)
    print('Using password:', password[:2] + '*' * (len(password) - 2))
    wlan.connect(ssid, password)

    # Wait for connect or fail after some retries if max_wait is set
    while wait == 0 or max_wait > 0:
        led.value(1)
        if wlan.status() >= 3:
            break
        if wlan.status() < 0:
            print('Wifi connection failed ' + str(wlan.status()) + ', retrying in 5 seconds...')
            time.sleep(5)
            reset_connection()
            wlan.connect(ssid, password)
        max_wait -= 1
        print('waiting for wifi connection...')
        time.sleep(1)
        led.value(0)

    print('connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )
    led.value(1)
    return status
