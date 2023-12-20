import toml

class ConfigReader:
    def __init__(self, override_config_path):
        self.default_config_path = "config-default.toml"
        self.override_config_path = override_config_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.default_config_path, 'r') as default_config_file:
            config_default = toml.load(default_config_file)
        with open(self.override_config_path, 'r') as override_config_file:
            config_override = toml.load(override_config_file)
        merged_config = {**config_default, **config_override}
        return merged_config        

    def get_config(self):
        return self.config
