
import json
from .Logger import logger
from ._types import Config

class ConfigLoader:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.log = logger
        self.config = {}

    def loading(self) -> Config:
        self.log.debug(f"Loading config from {self.config_file_path}")
        with open(self.config_file_path, "r") as f:
            self.config = json.load(f)
        self.log.debug(f"Config loaded: {self.config}")
        return self.config
    
    def update_config(self, key: str, value: str) -> bool:
        if key in self.config:
            self.config[key] = value
            self.log.debug(f"Config updated: {self.config}")
            return True
        else:
            self.log.warning(f"Key {key} not found in config")
            return False
        
    def save(self) -> bool:
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(self.config, f, indent=4)
            self.log.debug(f"Config saved to {self.config_file_path}")
            return True
        except Exception:
            self.log.exception("Error while saving config")
            return False