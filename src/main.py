# import microdot early to alloc needed memory
from microdot import Microdot, Response, redirect
from microdot.utemplate import Template
from mqtt_as import MQTTClient
from config import Config
from gasmeter import Gasmeter
from homeassistant import home_assistant

import gc
gc.collect()

import ntptime
from sys import platform
import asyncio
import machine
import micropython
import esp
esp.osdebug(None)
gc.collect()


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
      await client.publish(f'{config["topicPub"]}system/state', 'Online')
      asyncio.create_task(pulse())

async def pin_event(client, event):
  global pinReset
  while True:
     await event.wait()
     event.clear()
     pinReset = False

     gasmeter.do_counting()

     await client.publish(f'{config["topicPub"]}gasm3', str(gasmeter.gas_volume), retain=True)
     await client.publish(f'{config["topicPub"]}gaskWh', str(gasmeter.gas_energy), retain=True)
     print(f'pin: {reedPin.value()}, gaskWh: {gasmeter.gas_energy}, gasm3: {gasmeter.gas_volume}')
     asyncio.create_task(pulse())

async def main(client):
  global reedPin, pinReset
  await client.connect()
  if config["ntp"] != None:
    ntptime.host = config["ntp"]
    ntptime.settime()
  print(f'Connected to {config["server"]} MQTT broker')
  reedPin = machine.Pin(config["machinePin"], machine.Pin.IN, None)
  pinEvent = asyncio.Event()
  asyncio.create_task(pin_event(client, pinEvent))
  
  if config["homeassistant"]:
     asyncio.create_task(home_assistant(client, config["topicPub"]))
  await client.publish(f'{config["topicPub"]}gasm3', str(gasmeter.gas_volume), retain=True)
  await client.publish(f'{config["topicPub"]}gaskWh', str(gasmeter.gas_energy), retain=True)
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

conf = Config("config.json")
config = conf.config

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

gasmeter = Gasmeter("values.json")
valueJson = gasmeter.values

MQTTClient.DEBUG = True
client = MQTTClient(config)

# create webserver
app = Microdot()
Response.default_content_type = 'text/html'

@app.get('/')
async def mainSite(request):
  return await Template('index.tpl').render_async(valueJson=valueJson)

@app.post("/update")
async def update(request):
  if "change" in request.form:
    for key in request.form:
      if key == 'change':
        continue
      valueJson[key] = float(request.form[key])
    valueJson['gaskWh'] = gasmeter.calc_power()
    gasmeter.write_values()
    await client.publish(f'{config["topicPub"]}gasm3', str(gasmeter.gas_volume), retain=True)
    await client.publish(f'{config["topicPub"]}gaskWh', str(gasmeter.gas_energy), retain=True)
    gc.collect()
  elif "reboot" in request.form:
    machine.reset()
  return redirect("/")

try:
  start()
except:
  app.shutdown()
  client.close()
  blue_led(True)