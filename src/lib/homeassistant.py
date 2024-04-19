import ujson
import gc

async def home_assistant(client, baseTopic):
   payload_m3= {
      "device_class": "gas",
      "state_class": "total_increasing",
      "state_topic": f"{baseTopic}gasm3",
      "unit_of_measurement": "m\u00b3",
      "value_template": "{{ value }}",
      "unique_id": "esp32GasMeter_gas",
      "device": {
         "identifiers": [
            "esp32_Gasmeter"
         ],
         "name": "Gasmeter",
      }
   }
   payload_kWh= {
      "device_class": "energy",
      "state_class": "total_increasing",
      "state_topic": f"{baseTopic}gaskWh",
      "unit_of_measurement": "kWh",
      "value_template": "{{ value }}",
      "unique_id": "esp32GasMeter_energy",
      "device": {
         "identifiers": [
            "esp32_Gasmeter"
         ],
         "name": "Gasmeter",
      }
   }
   haTopicm3= 'homeassistant/sensor/esp32GasMeter/gas/config'
   haTopickWh= 'homeassistant/sensor/esp32GasMeter/energy/config'
   json_payload_m3 = ujson.dumps(payload_m3).encode('utf8') # need encoding for superscript 3
   json_payload_kwH = ujson.dumps(payload_kWh)
   await client.publish(f'{haTopicm3}', json_payload_m3, retain=True)
   await client.publish(f'{haTopickWh}', json_payload_kwH, retain=True)
   gc.collect()
