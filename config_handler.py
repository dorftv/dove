import toml
import argparse

class ConfigReader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            self = super(ConfigReader, cls).__new__(cls)
            self.default_config_path = "config-default.toml"
            parser = argparse.ArgumentParser()
            parser.add_argument("-c", "--config", action="store", type=str, required=False)
            self.args = parser.parse_args()
            self.config = self.load_config()
            cls._instance = self
        return cls._instance

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def load_config(self):
        with open(self.default_config_path, 'r') as default_config_file:
            config_default = toml.load(default_config_file)
        if self.args.config is not None:
            self.override_config_path = self.args.config
            with open(self.override_config_path, 'r') as override_config_file:
                config_override = toml.load(override_config_file)
                self._deep_merge(config_default, config_override)
        # Normalize preview type: string → list for backward compat
        if 'preview' in config_default:
            for key, cfg in config_default['preview'].items():
                if isinstance(cfg, dict) and 'type' in cfg and isinstance(cfg['type'], str):
                    cfg['type'] = [cfg['type']]
        return config_default


    def get_config(self):
        return self.config

    def get_preview_config(self, type):
        if type in self.config['preview']:
            return self.config['preview'][type]
        return None

    def get_preview_enabled(self):
        return self.config.get('main', {}).get('preview_enabled', True)

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
            return [k for k, v in self.config['scenes'].items() if isinstance(v, dict)]
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

    def get_encoders(self):
        if 'encoders' in self.config:
            return self.config['encoders']
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
        return self.config.get('resolutions', {})

    def get_default_resolution(self):
        default_resolution = self.config.get('main', {}).get('default_resolution', 'HD720')
        resolutions = self.get_resolutions()
        return resolutions.get(default_resolution, {'width': 1280, 'height': 720})

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
        return self.config.get('main', {}).get('hls_path', '/var/dove/hls')

    def get_scene_fallback_pattern(self):
        return self.config.get('scenes', {}).get('fallback_pattern', 2)

    def get_auth_config(self):
        defaults = {
            'enabled': False,
            'issuer': '',
            'client_id': '',
            'client_secret': '',
            'cookie_secret': '',
            'cookie_secure': True,
            'allowed_origins': [],
            'api_tokens': [],
            'groups': {
                'user': 'dove-user',
                'supervisor': 'dove-supervisor',
                'outputs': 'dove-outputs',
                'admin': 'dove-admin',
            },
        }
        if 'auth' in self.config:
            auth = self.config['auth']
            for k, v in auth.items():
                if k == 'groups' and isinstance(v, dict):
                    defaults['groups'].update(v)
                elif k == 'api_tokens' and isinstance(v, list):
                    defaults['api_tokens'] = v
                else:
                    defaults[k] = v
        # Allow env var overrides
        import os
        if os.environ.get('AUTH_ENABLED', '').lower() in ('true', '1'):
            defaults['enabled'] = True
        for key in ('issuer', 'internal_issuer', 'client_id', 'client_secret', 'cookie_secret'):
            env_val = os.environ.get(f'AUTH_{key.upper()}')
            if env_val:
                defaults[key] = env_val
        if os.environ.get('AUTH_COOKIE_SECURE', '').lower() in ('false', '0'):
            defaults['cookie_secure'] = False
        env_origins = os.environ.get('AUTH_ALLOWED_ORIGINS')
        if env_origins:
            defaults['allowed_origins'] = [o.strip() for o in env_origins.split(',') if o.strip()]
        # Single API token from env var (convenience for Docker)
        env_token = os.environ.get('AUTH_API_TOKEN')
        if env_token:
            defaults['api_tokens'].append({
                'token': env_token,
                'name': os.environ.get('AUTH_API_TOKEN_NAME', 'env-token'),
                'role': os.environ.get('AUTH_API_TOKEN_ROLE', 'admin'),
            })
        # internal_issuer defaults to issuer (same URL when no Docker split needed)
        if not defaults.get('internal_issuer'):
            defaults['internal_issuer'] = defaults['issuer']
        return defaults

    def get_nodecg_config(self):
        """Return NodeCG config if configured, None otherwise."""
        import os
        url = os.environ.get('NODECG_URL')
        if url:
            return {'url': url.rstrip('/')}
        cfg = self.config.get('proxy', {}).get('nodecg', {})
        if cfg.get('url'):
            return {'url': cfg['url'].rstrip('/')}
        return None

    def get_enable_video(self):
        return self.config.get('main', {}).get('enable_video', True)

    def get_enable_audio(self):
        return self.config.get('main', {}).get('enable_audio', True)

    def get_webrtc_config(self):
        defaults = {
            'stun_server': None,
            'turn_server': None,
            'turn_user': None,
            'turn_password': None,
            'min_rtp_port': 10000,
            'max_rtp_port': 10100,
        }
        if 'webrtc' in self.config:
            defaults.update(self.config['webrtc'])
        return defaults