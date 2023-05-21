import utime
import ntptime
import ujson
from sys import platform
from mqtt_as import MQTTClient, config
import uasyncio
from microdot_asyncio import Microdot, Response
from microdot_utemplate import render_template
import machine
import micropython
import esp
esp.osdebug(None)
import gc

def dumpJson(jsonData: dict, fileName: str):
  """
  simply dump dictionary to json file
  """
  wFile = open(fileName, 'w')
  wFile.write(ujson.dumps(jsonData))
  wFile.close()

def calcGas(gasm3: float) -> float:
  """
  calculation m3 to kWh
  """
  result = gasm3 * valueJson['brennzahl'] * valueJson['zustandszahl']
  return result

interDetect = False
def handlerInterrupt(timer):
  """
  interrupt handler of our input gpio
  """
  global interDetect, gasm3, gaskWh
  # emp interrupts are really short, so check pin.value() again to filter those interrupts
  print('pin value: ', reedPin.value())
  if reedPin.value() == 1:
     print("possible bounce or emp interrupt filtered")
     return
  print('send data')
  gasm3 = valueJson['gasm3'] + valueJson['impulsm3']
  gaskWh = calcGas(gasm3)
  valueJson['gasm3'], valueJson['gaskWh'] = gasm3, gaskWh
  interDetect = True
  dumpJson(valueJson,'values.json')

# debouncing
def input_debounce(pin):
    #print('pin: ', pin, 'value: ', pin.value())
    if pin.value() == 0:
      # set Timer to prevent repeating interrupt (period in Millisekunden)
      machine.Timer(0).init(mode=machine.Timer.ONE_SHOT, period=500, callback=handlerInterrupt)

async def pulse():
  """
  let pulse the blue led
  """
  blue_led(False)
  await uasyncio.sleep(1)
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
      uasyncio.create_task(pulse())

async def main(client):
  global interDetect, reedPin
  await client.connect()
  if ntp != None:
    ntptime.settime()
  print(f'Connected to {config["server"]} MQTT broker')
  reedPin = machine.Pin(config["machinePin"], machine.Pin.IN, None)
  # interupt event on input, call callbackInput function
  reedPin.irq(trigger=machine.Pin.IRQ_FALLING, handler=input_debounce)
  while True:
    if interDetect:
      await client.publish(f'{topicPub}gasm3', str(gasm3))
      await client.publish(f'{topicPub}gaskWh', str(gaskWh))
      uasyncio.create_task(pulse())
      interDetect = False
    await uasyncio.sleep(1)

def start():
  loop= uasyncio.get_event_loop()
  for task in (up, down, main):
        loop.create_task(task(client))
  loop.create_task(app.start_server(port=80))
  loop.run_forever()

########## entry point ##########

gc.collect()

# merge mqtt_as config with our config.json for defaulting some settings
configRead = open('config.json').read()
configJson = ujson.loads(configRead)
config.update(configJson)

# many vars i currently dont need to define with default. many defaults come from mqtt_as
topicPub = config["topicPub"] if "topicPub" in config else 'esp32gas/'
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

valueJson = ujson.loads(valuesRead)
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
  return render_template('index.tpl', valueJson=valueJson)

try:
  start()
except:
  app.shutdown()
  client.close()
  blue_led(True)