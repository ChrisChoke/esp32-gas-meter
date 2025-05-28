from mqtt_as import config

import json

class FileHandler():
    def __init__(self, filename):
        self.filename: str = filename
        
    def read(self) -> str:
        with open(self.filename, "r") as file:
            data: str = file.read()
        return data

    def write(self, data) -> None:
        with open(self.filename, "w") as file:
            file.write(data)
        return None


class Config(FileHandler):
    def __init__(self, file_name: str):
        super().__init__(file_name)
        self.config: dict = self._load_config()
    
    def _load_config(self) -> dict:
        file_data: str = super().read()
        data_: dict = json.loads(file_data)
        config.update(data_)

        # defaulting some config options
        config["topicPub"] = config.get("topicPub", "esp32gas/")
        config["homeassistant"] = config.get("homeassistant", False)
        config["ntp"] = config.get("ntp", None)
        config["queue_len"] = 1
        config['will'] = ( f'{config["topicPub"]}system/state', 'Offline', False, 0 )

        return config



