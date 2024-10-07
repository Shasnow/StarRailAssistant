
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