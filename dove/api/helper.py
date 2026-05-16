import os
import pkgutil
import importlib
import threading
from fastapi import APIRouter, HTTPException
from typing import Generator, Tuple, Type, Dict, Set, Any, Optional, Union, List, get_args, get_origin, Annotated
from dove.api.output_models import OutputDTO
from dove.api.input_models import InputDTO
import inspect
from pydantic import BaseModel
from dove.api.encoder import audio_encoder
from dove.api.encoder import video_encoder
from dove.api.encoder import mux

from dove.config_handler import ConfigReader

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


config = ConfigReader()

def get_module_classes(module, base_class):
    return [
        (name, obj) for name, obj in inspect.getmembers(module)
        if inspect.isclass(obj) and issubclass(obj, base_class) and obj != base_class
    ]

_encoder_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
_encoder_availability_cache: Dict[str, bool] = {}

# Hardware encoders need READY probe (plugin exists but hardware may not)
_HARDWARE_ENCODERS = {
    "vah264enc", "vah264lpenc", "vah265enc",
    "vaapih264enc", "vaapih265enc",
    "vulkanh264enc", "vulkanh265enc",
    "mpph264enc",
}

# Auto-detection priority (best first)
AUTO_PRIORITY = {
    "h264": ["vah264enc", "vah264lpenc", "vaapih264enc", "vulkanh264enc", "openh264enc", "x264enc"],
    "h265": ["vah265enc", "vaapih265enc", "vulkanh265enc", "x265enc"],
    "vp8":  ["vp8enc"],
    "vp9":  ["vp9enc"],
    "av1":  ["av1enc"],
}


def _probe_hardware_encoder(factory) -> bool:
    """Probe encoder factory via READY transition. GLib thread only."""
    quiet_handler = GLib.log_set_handler(
        "GStreamer",
        GLib.LogLevelFlags.LEVEL_ERROR | GLib.LogLevelFlags.LEVEL_WARNING,
        lambda *a: True, None,
    )
    try:
        elem = factory.create(None)
        if not elem:
            return False
        ret = elem.set_state(Gst.State.READY)
        available = ret != Gst.StateChangeReturn.FAILURE
        elem.set_state(Gst.State.NULL)
        return available
    except Exception:
        return False
    finally:
        GLib.log_remove_handler("GStreamer", quiet_handler)


def _is_encoder_available(element_name: str) -> bool:
    """Software: factory.find() suffices. Hardware: READY probe on GLib thread."""
    if element_name in _encoder_availability_cache:
        return _encoder_availability_cache[element_name]

    factory = Gst.ElementFactory.find(element_name)
    if not factory:
        _encoder_availability_cache[element_name] = False
        return False

    if element_name not in _HARDWARE_ENCODERS:
        _encoder_availability_cache[element_name] = True
        return True

    if threading.current_thread() is threading.main_thread():
        available = _probe_hardware_encoder(factory)
    else:
        result = {}
        done = threading.Event()
        def _run():
            result['v'] = _probe_hardware_encoder(factory)
            done.set()
            return False
        GLib.idle_add(_run)
        if not done.wait(timeout=5.0):
            from dove.logger import logger
            logger.log(f"Encoder probe for {element_name} timed out", level='WARNING')
            return False  # don't cache timeout — retry next call

        available = result['v']

    _encoder_availability_cache[element_name] = available
    return available


def get_auto_encoder(codec: str) -> Optional[str]:
    """Return best available encoder element name for a codec, or None."""
    for element_name in AUTO_PRIORITY.get(codec, []):
        if _is_encoder_available(element_name):
            return element_name
    return None


def get_encoder_types() -> Dict[str, List[Dict[str, Any]]]:
    global _encoder_cache
    if _encoder_cache is not None:
        return _encoder_cache

    if not Gst.is_initialized():
        Gst.init([])
    encoders = {"audio": [], "video": [], "mux": []}

    audio_classes = get_module_classes(audio_encoder, audio_encoder.audioEncoderDTO)
    video_classes = get_module_classes(video_encoder, video_encoder.videoEncoderDTO)
    mux_classes = get_module_classes(mux, mux.muxDTO)

    encoder_classes = audio_classes + video_classes + mux_classes

    for name, obj in encoder_classes:
        if issubclass(obj, audio_encoder.audioEncoderDTO):
            encoder_type = "audio"
        elif issubclass(obj, video_encoder.videoEncoderDTO):
            encoder_type = "video"
        elif issubclass(obj, mux.muxDTO):
            encoder_type = "mux"
        else:
            continue

        encoder_fields = get_fields(obj, "dove.api.encoder")
        element_name = encoder_fields.get("element", {}).get("default")

        if element_name and _is_encoder_available(element_name):
            encoder_info = {
                "name": encoder_fields.get("name", {}).get("default", name),
                "element": element_name,
                "fields": encoder_fields
            }
            encoders[encoder_type].append(encoder_info)

    _encoder_cache = encoders
    return encoders


_encoder_dto_map: Optional[Dict[str, type]] = None

def get_encoder_dto_class(element_name: str) -> Optional[type]:
    """Look up encoder DTO class by GStreamer element name."""
    global _encoder_dto_map
    if _encoder_dto_map is None:
        _encoder_dto_map = {}
        for _, cls in get_module_classes(video_encoder, video_encoder.videoEncoderDTO):
            elem_field = cls.model_fields.get('element')
            if elem_field and elem_field.default:
                _encoder_dto_map[elem_field.default] = cls
        for _, cls in get_module_classes(audio_encoder, audio_encoder.audioEncoderDTO):
            elem_field = cls.model_fields.get('element')
            if elem_field and elem_field.default:
                _encoder_dto_map[elem_field.default] = cls
    return _encoder_dto_map.get(element_name)


def get_model_fields(models_path: str, exclude_models: Set[str] = set()) -> dict:
    model_fields = {}
    enabled_models = (config.get_enabled_outputs() if models_path == "dove.api.outputs"
                      else config.get_enabled_inputs() if models_path == "dove.api.inputs"
                      else [])

    for model, model_name in get_models(models_path, exclude_models, enabled_models):
        raw_fields = model.model_json_schema().get('properties', {})
        model_type = raw_fields.get('type', {}).get('default')
        if model_type:
            model_fields[model_type] = {
                "label": model_type,
                "fields": get_fields(model, models_path)
            }

    return {k: model_fields[k] for k in enabled_models if k in model_fields} if enabled_models else model_fields



def get_fields(model_class: type(BaseModel), models_path: str) -> dict:
    if not issubclass(model_class, BaseModel):
        raise TypeError("Class must be a subclass of pydantic.BaseModel")

    properties = model_class.model_json_schema().get('properties', {})
    required_fields = model_class.model_json_schema().get('required', {})
    parent_fields = {
        "dove.api.outputs": OutputDTO.model_json_schema().get('properties', {}),
        "dove.api.inputs": InputDTO.model_json_schema().get('properties', {})
    }.get(models_path, {})

    def get_option_name(option):
        if isinstance(option, str):
            return option
        return option.model_json_schema().get('properties', {}).get('name', {}).get('default', option.__name__)

    def extract_union_types(field_type):
        if get_origin(field_type) is Annotated:
            field_type = get_args(field_type)[0]
        if get_origin(field_type) is Union:
            return [arg for arg in get_args(field_type) if isinstance(arg, type) and issubclass(arg, BaseModel)]
        elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return [field_type]
        return []

    fields = {}
    for name, field in properties.items():
        # Include child-only fields, 'type', and encoder fields overridden with constraints
        is_encoder_override = name in ("video_encoder", "audio_encoder") and name in model_class.__annotations__
        if name not in parent_fields or name == "type" or is_encoder_override:
            anyOf = next((item['type'] for item in field.get('anyOf', []) if isinstance(item, dict) and 'type' in item), None)
            field_info = {
                "name": name,
                "label": field.get('label', name),
                "description": field.get('description'),
                "help": field.get('help'),
                "placeholder": field.get('placeholder'),
                "default": field.get('default'),
                "type": field.get("type", anyOf),
                "hidden": field.get("hidden", False),
                "required": name in required_fields,
                "enum": field.get("enum"),
            }

            if name in ["video_encoder", "audio_encoder", "mux"]:
                field_type = model_class.model_fields[name].annotation
                allowed_options = []

                if get_origin(field_type) is Union:
                    for arg in get_args(field_type):
                        allowed_options.extend(extract_union_types(arg))
                else:
                    allowed_options.extend(extract_union_types(field_type))

                options = list(dict.fromkeys([get_option_name(option) for option in allowed_options]))

                default_value = None
                default_factory = model_class.model_fields[name].default_factory
                if default_factory:
                    default_value = default_factory.__name__.replace('lambda:', '').strip().split('(')[0]
                elif field.get('default') is not None:
                    default_value = get_option_name(field['default'].__class__)

                field_info["options"] = options
                field_info["default"] = default_value

            fields[name] = field_info

    return fields

def get_models(models_path: str, exclude_models: Set[str] = set(), enabled_models: List[str] = None) -> Generator[Tuple[Type[BaseModel], str], None, None]:
    exclude_models.add("BaseModel")
    package = importlib.import_module(models_path)
    package_dir = package.__path__[0]

    for root, _, _ in os.walk(package_dir):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, package_dir).replace(os.sep, '.')
            full_module_name = f"{models_path}.{module_path}.{module_name}" if module_path != '.' else f"{models_path}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and (issubclass(obj, OutputDTO) or issubclass(obj, InputDTO)):
                        model_type = obj.model_json_schema().get('properties', {}).get('type', {}).get('default')
                        if not enabled_models or model_type in enabled_models:
                            yield obj, name
            except ModuleNotFoundError as e:
                raise e

def get_dtos(io_type: str) -> Generator[Tuple[Type[BaseModel], str], None, None]:
    base_path = f'dove.api.{io_type}s'
    base_class = InputDTO if io_type == 'input' else OutputDTO

    package = importlib.import_module(base_path)
    for _, name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f'{base_path}.{name}')
        for attr_name, attr_value in module.__dict__.items():
            if isinstance(attr_value, type) and issubclass(attr_value, base_class) and attr_value != base_class:
                yield attr_value, attr_name.lower().replace(f'{io_type}dto', '')

def get_routers(routes_path: str) -> Generator[Tuple[APIRouter, str], None, None]:
    package = importlib.import_module(routes_path)
    routes_dir = package.__path__[0]
    for root, _, _ in os.walk(routes_dir):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, routes_dir).replace(os.sep, '.')
            full_module_name = f"{routes_path}.{module_path}.{module_name}" if module_path != '.' else f"{routes_path}.{module_name}"

            module = importlib.import_module(full_module_name)
            if hasattr(module, 'router'):
                yield module.router, module_name


async def create_or_raise(handler, entity):
    """Await dynamic entity build; raise HTTP 500 with the failure detail on error."""
    try:
        fut = handler.add_pipeline(entity)
        if fut is not None:
            success = await fut
            if not success:
                detail = getattr(entity.data, "details", None) or f"Failed to create {entity.data.type}"
                entity_type = getattr(entity.data, "type", None) or "entity"
                raise HTTPException(status_code=500, detail=f"{entity_type}: {detail}")
    except HTTPException:
        raise
    except Exception as e:
        entity_type = getattr(entity.data, "type", None) or "entity"
        raise HTTPException(status_code=500, detail=f"{entity_type}: {e}")
