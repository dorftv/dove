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
        if self.args.config is not None:
            self.override_config_path = self.args.config
            with open(self.override_config_path, 'r') as override_config_file:
                config_override = toml.load(override_config_file)
                for section, values in config_override.items():
                    if section in config_default:
                        config_default[section].update(values)
                    else:
                        config_default[section] = values
        return config_default


    def get_config(self):
        return self.config

    def get_preview_config(self, type):
        if type in self.config['preview']:
            return self.config['preview'][type]
        return None

    def get_preview_enabled(self):
        return self.config.preview_enabled

    def get_enabled_outputs(self):
        if 'ui' in self.config:
            if 'enabled_outputs' in self.config['ui']:
                return self.config['ui']['enabled_outputs']
        return []

    def get_enabled_inputs(self):
        if 'ui' in self.config:
            if 'enabled_inputs' in self.config['ui']:
                return self.config['ui']['enabled_inputs']
        return []

    def get_proxies(self):
        if 'srtrelay' in self.config:
            return True
        else:
            return False

    def get_proxy_types(self):
        if 'proxy' in self.config:
            items = []
            for key, item in self.config['proxy'].items():
                items.append(key)
            return items
        return []

    def get_proxy(self, proxy_type):
        if proxy_type in self.config['proxy']:
            return list(self.config['proxy'][proxy_type].keys())
        return []

    def get_proxy_details(self, proxy_type, proxy_name):
        # Get specific proxy details
        if proxy_type in self.config['proxy'] and proxy_name in self.config['proxy'][proxy_type]:
            return self.config['proxy'][proxy_type][proxy_name]
        return None

    def get_scenes(self):
        if 'scenes' in self.config:
            return list(self.config['scenes'].keys())
        else:
            return []

    def get_scene_details(self, scene_name):
        if 'scenes' in self.config and scene_name in self.config['scenes']:
            return self.config['scenes'][scene_name]
        else:
            return None

    def get_scene_inputs(self, scene_name):
        scene_section = scene_name
        inputs = {}

        for section, values in self.config['scenes'].items():
            if section == scene_section:
                for key, value in values.items():
                    if isinstance(value, dict):
                        inputs[key] = value
        return inputs

    def get_input_details(self, scene_name, input_name):
        scene_inputs = self.get_scene_inputs(scene_name)
        if scene_inputs and input_name in scene_inputs:
            return scene_inputs[input_name]
        else:
            return None

    def get_inputs(self):
        if 'inputs' in self.config:
            return self.config['inputs']
        else:
            return None

    def get_outputs(self):
        if 'outputs' in self.config:
            return self.config['outputs']
        else:
            return None

    def get_program_overlays(self):
        if 'program' in self.config:
            return self.config['program']
        else:
            return None


    def get_resolutions(self):
        return self.config['resolutions']

    def get_default_resolution(self):
        default_resolution = self.config['main']['default_resolution']
        resolutions = self.get_resolutions()
        return resolutions[default_resolution]

    def get_default_height(self) -> int:
        return self.get_default_resolution()['height']

    def get_default_width(self) -> int:
        return self.get_default_resolution()['width']

    def get_preview_resolution(self):
        preview_resolution = self.config['main']['preview_resolution']
        resolutions = self.get_resolutions()
        return resolutions[preview_resolution]

    def get_default_framerate(self):
        default_framerate = self.config['main']['default_framerate']
        return default_framerate

    def get_default_audio_format(self):
        audio_format = self.config['main']['audio_format']
        return audio_format

    def get_default_audio_rate(self):
        audio_rate = self.config['main']['audio_rate']
        return audio_rate

    def get_default_audio_channels(self):
        audio_channels = self.config['main']['audio_channels']
        return audio_channels

    def get_default_volume(self):
        default_volume = self.config['main']['volume']
        return default_volume

    def get_hls_path(self):
        hls_path = self.config['main']['hls_path']
        return hls_path