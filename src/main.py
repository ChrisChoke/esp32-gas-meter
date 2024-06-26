# import microdot early to alloc needed memory
from microdot import Microdot, Response
from microdot.utemplate import Template
from mqtt_as import MQTTClient, config
from homeassistant import home_assistant

import gc
gc.collect()

import ntptime
import json
from sys import platform
import asyncio
import machine
import micropython
import esp
esp.osdebug(None)
gc.collect()

def dumpJson(jsonData: dict, fileName: str):
  """
  simply dump dictionary to json file
  """
  wFile = open(fileName, 'w')
  wFile.write(json.dumps(jsonData))
  wFile.close()

def calcGas(gasm3: float) -> float:
  """
  calculation m3 to kWh
  """
  result = gasm3 * valueJson['brennzahl'] * valueJson['zustandszahl']
  return result

async def pulse():
  """
  let pulse the blue led
  """
  blue_led(False)
  await asyncio.sleep(1)
  blue_led(True)

async def down(client):
  """
  coroutine for connection down
  """
  while True:
      await client.down.wait()  # Pause until connectivity changes
      client.down.clear()
      wifi_led(False)
      print('WiFi or broker is down.')

async def up(client):
  """
  coroutine for connection up
  """
  while True:
      await client.up.wait()
      client.up.clear()
      wifi_led(True)
      await client.publish(f'{topicPub}system/state', 'Online')
      asyncio.create_task(pulse())

async def count_up(m3: float, impulsm3: float) -> float:
   # function to try to prevent floating point error
   # convert as string to integer without any calculation and count up
   imp_str = str(impulsm3)
   _decimal = imp_str[imp_str.index(".")+1:]
   decimal = len(_decimal)

   multiplier = 10**decimal
   str_formatter = f'{{:.{decimal}f}}'
   _m3_str = str_formatter.format(m3)
   m3_str = _m3_str.replace(".", "")
   
   result = int(int(m3_str) + (impulsm3 * multiplier))
   return result / multiplier

async def pin_event(client, event):
  global pinReset
  while True:
     await event.wait()
     event.clear()
     pinReset = False

     gasm3 = await count_up(valueJson['gasm3'], valueJson['impulsm3'])
     gaskWh = calcGas(gasm3)
     valueJson['gasm3'], valueJson['gaskWh'] = gasm3, gaskWh
     dumpJson(valueJson,'values.json')

     await client.publish(f'{topicPub}gasm3', str(gasm3))
     await client.publish(f'{topicPub}gaskWh', str(gaskWh))
     print(f'pin: {reedPin.value()}, gaskWh: {gaskWh}, gasm3: {gasm3}')
     asyncio.create_task(pulse())

async def main(client):
  global reedPin, pinReset
  await client.connect()
  if ntp != None:
    ntptime.settime()
  print(f'Connected to {config["server"]} MQTT broker')
  reedPin = machine.Pin(config["machinePin"], machine.Pin.IN, None)
  pinEvent = asyncio.Event()
  asyncio.create_task(pin_event(client, pinEvent))
  
  if homeAssistant:
     asyncio.create_task(home_assistant(client, topicPub))
  await client.publish(f'{topicPub}gasm3', str(gasm3))
  await client.publish(f'{topicPub}gaskWh', str(gaskWh))
  pinReset = True
  while True:
    if reedPin.value() == 0 and pinReset:
       pinEvent.set()
    elif reedPin.value() == 1:
       pinReset = True
    await asyncio.sleep(0.3)

def start():
  loop= asyncio.get_event_loop()
  for task in (up, down, main):
        loop.create_task(task(client))
  loop.create_task(app.start_server(port=80))
  loop.run_forever()

########## entry point ##########

gc.collect()

# merge mqtt_as config with our config.json for defaulting some settings
configRead = open('config.json').read()
configJson = json.loads(configRead)
config.update(configJson)

# many vars i currently dont need to define with default. many defaults come from mqtt_as
topicPub = config["topicPub"] if "topicPub" in config else 'esp32gas/'
homeAssistant = config["homeassistant"] if "homeassistant" in config else False
ntp = config["ntp"] if "ntp" in config else None

# set up webrepl if password in config.json
if config["webreplpw"]:
    try:
        import webrepl_cfg
    except ImportError:
        try:
            with open("webrepl_cfg.py", "w") as f:
                f.write("PASS = %r\n" % config["webreplpw"])
        except Exception as e:
            print("Can't start webrepl: {!s}".format(e))
    try:
        import webrepl

        webrepl.start()
    except Exception as e:
        print("Can't start webrepl: {!s}".format(e))

# setup red and blue led which can connected to the board
if platform == 'esp8266' or platform == 'esp32':
    from machine import Pin
    def ledfunc(pin, active=0):
        pin = pin
        def func(v):
            pin(not v)  # Active low on ESP8266
        return pin if active else func
    wifi_led = ledfunc(Pin(0, Pin.OUT, value = 1))  # Red LED for WiFi fail/not ready yet
    blue_led = ledfunc(Pin(2, Pin.OUT, value = 0))  # Message send

try:
  valuesRead = open('values.json').read()
except OSError:
  defaultValues = {"gasm3": 1000.00, "gaskWh": 1000.00, "brennzahl": 11.537 , "zustandszahl": 0.95, "impulsm3": 0.01}
  dumpJson(defaultValues, 'values.json')
  valuesRead = open('values.json').read()

valueJson = json.loads(valuesRead)
gasm3, gaskWh = valueJson['gasm3'], valueJson['gaskWh']

ntptime.host = ntp

config["queue_len"] = 1
config['will'] = ( f'{topicPub}system/state', 'Offline', False, 0 )
MQTTClient.DEBUG = True
client = MQTTClient(config)

# create webserver
app = Microdot()
Response.default_content_type = 'text/html'

@app.route('/', methods=['GET', 'POST'])
async def mainSite(request):
  if request.method == "POST":
    print(request)
    if "change" in request.form:
      for key in request.form:
        if key == 'change':
          continue
        else:
          valueJson[key] = float(request.form[key])
      valueJson['gaskWh'] = calcGas(valueJson['gasm3'])
      dumpJson(valueJson, 'values.json')
      await client.publish(f'{topicPub}gasm3', str(valueJson['gasm3']))
      await client.publish(f'{topicPub}gaskWh', str(valueJson['gaskWh']))
      gc.collect()
    elif "reboot" in request.form:
      machine.reset()
  return await Template('index.tpl').render_async(valueJson=valueJson)

try:
  start()
except:
  app.shutdown()
  client.close()
  blue_led(True)