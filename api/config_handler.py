import toml
import argparse

class ConfigReader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            self = super(ConfigReader, cls).__new__(cls)
            self.default_config_path = "config-default.toml"
            parser = argparse.ArgumentParser()
            parser.add_argument("--config", action="store", type=str, required=False)
            self.args = parser.parse_args()
            self.config = self.load_config()
            cls._instance = self
        return cls._instance

    def load_config(self):
        with open(self.default_config_path, 'r') as default_config_file:
            config_default = toml.load(default_config_file)
            merged_config = config_default
        if self.args.config is not None:
            self.override_config_path = self.args.config
            with open(self.override_config_path, 'r') as override_config_file:
                config_override = toml.load(override_config_file)
                merged_config = {**config_default, **config_override}
        return merged_config
        
    def get_config(self):
        return self.config

    # @TODO use real value
    def get_preview_enabled(self):
        #print(self.config.preview_enabled)
        return True

    def get_mixers(self):
        if 'mixers' in self.config:
            return self.config['mixers']
        else:
            return None


    def get_resolutions(self):
        return self.config['resolutions']

    def get_default_resolution(self):
        default_resolution = self.config['main']['default_resolution']
        resolutions = self.get_resolutions()
        return resolutions[default_resolution]

    def get_preview_resolution(self):
        preview_resolution = self.config['main']['preview_resolution']
        resolutions = self.get_resolutions()
        return resolutions[preview_resolution]        

    def get_default_volume(self):
        default_volume = self.config['main']['default_volume']
        return default_volume