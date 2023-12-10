# ESP32-Gas-Meter

I dropped interrupt (pin.irq) for detecting state of reed contact, because i had much trouble with emc. So i go to reading the pin.value() every 500ms. i hope that is more robust.
i let the interrupt version in another branch. so check out if you are interested.

codebase is a bit unordered and unstructured. feel free to clean it up before i do someday :-)
its my first async codebase, so i am in learning process :-)

## Instructions

This project is for esp32 platform. It read the reed-contact of your gas meter from your supplier and publish it via mqtt.
in germany our gas meter has possibility for inserting a reed-contact to count pulses to increase gas m³.

you can set up some values via webserver. So you must get ESPs Ip-Address via your dhcp server or router.

**Notice:** The position of the reed contact is a bit sensitive. A bit too more right or left could end in double count or
 not every pulse will count. Means, the signal will be very unstable. So please leave a bit more time to check the right position.

 The reed contact pin is pull-up connected with external resistor.

### main.py:

Includes the Main code.

you can connect on Pin 0 a red LED and on Pin 2 a blue LED to check if wifi is down (red led turn on) and if a
mqtt message is sent (blue led pulse for 1 sec)

wifi_led = ledfunc(Pin(0, Pin.OUT, value = 1))  # Red LED for WiFi fail/not ready yet
blue_led = ledfunc(Pin(2, Pin.OUT, value = 0))  # Message send

### config.json:

The `config.json` includes your configuration in json-format.
You have to create one in the root before first run.

possible configs:

```
{
    "ssid" : "YOUR_SSID",
    "wifi_pw" : "YOUR_PASSWORD",
    "machinePin" : 32,
    "server" : "IP_ADDRESS",
    "port" : 1111,              // default 1883
    "user" : "USERNAME",        // default None
    "password" : "PASSWORD",      // default None
    "ntp": "IP_ADDRESS or DNS",     // default None
    "topicPub" : "esp32/",           // default "esp32gas/"
    "webreplpw": "REPLPASSWORD"
    "homeassistant": true        // default false
}
```

### values.json

the values.json saved all important values we need.

gaskWh is just here to save last value of it. the application calculate it with :

gasm3 * zustandszahl * brennzahl = gaskWh.
zustandszahl and brennzahl you get from the invoice from your supplier.
impulsm3 you get from the gas meter of your supplier.

sorry for the german words. i currently dont know what are the english words :-)

```
{
    "gasm3": 1000.00,
    "gaskWh": 1000.00,
    "brennzahl": 11.537 ,
    "zustandszahl": 0.95,
    "impulsm3": 0.01
}
```

### MQTT

you will get following mqtt topics:

#### esp32gas/gasm3

get the gas usage in m³.

#### esp32gas/gaskWh

get the gas usage in kWh.

#### esp32gas/system/state
get the connection state to mqtt-broker:</br>

'Online' or </br>
'Offline'