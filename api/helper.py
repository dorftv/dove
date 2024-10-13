import os
import pkgutil
import importlib
from fastapi import APIRouter, Request
from typing import Generator, Tuple, Type, Dict, Set, Any, Optional, Union, List, get_args, get_origin, Annotated
from api.output_models import OutputDTO
from api.input_models import InputDTO
import inspect
from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.outputs.output import Output
from pydantic import BaseModel
import json
from pydantic.fields import FieldInfo
from api.encoder import encoder
from api.encoder import audio_encoder
from api.encoder import video_encoder
from api.encoder import mux

from config_handler import ConfigReader

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


config = ConfigReader()

def get_module_classes(module, base_class):
    return [
        (name, obj) for name, obj in inspect.getmembers(module)
        if inspect.isclass(obj) and issubclass(obj, base_class) and obj != base_class
    ]

def get_encoder_types() -> Dict[str, List[Dict[str, Any]]]:
    Gst.init(None)
    encoders = {"audio": [], "video": [], "mux": []}

    # Get all encoder classes from the submodules
    audio_classes = get_module_classes(audio_encoder, audio_encoder.audioEncoderDTO)
    video_classes = get_module_classes(video_encoder, video_encoder.videoEncoderDTO)
    mux_classes = get_module_classes(mux, mux.muxDTO)

    encoder_classes = audio_classes + video_classes + mux_classes

    def quiet_log_handler(domain, level, message, user_data):
        return True

    log_handler_id = GLib.log_set_handler("GStreamer", GLib.LogLevelFlags.LEVEL_ERROR, quiet_log_handler, None)

    try:
        for name, obj in encoder_classes:
            if issubclass(obj, audio_encoder.audioEncoderDTO):
                encoder_type = "audio"
            elif issubclass(obj, video_encoder.videoEncoderDTO):
                encoder_type = "video"
            elif issubclass(obj, mux.muxDTO):
                encoder_type = "mux"
            else:
                continue

            encoder_fields = get_fields(obj, "api.encoder")
            element_name = encoder_fields.get("element", {}).get("default")

            # Check if the element can be created
            if element_name:
                element = Gst.ElementFactory.make(element_name, None)
                if element is not None:
                    encoder_info = {
                        "name": encoder_fields.get("name", {}).get("default", name),
                        "element": element_name,
                        "fields": encoder_fields
                    }
                    encoders[encoder_type].append(encoder_info)

    finally:
        GLib.log_remove_handler("GStreamer", log_handler_id)

    return encoders


def get_encoder_names(encoder_type: str) -> List[str]:
    encoder_types = get_encoder_types()

    return [encoder["name"] for encoder in encoder_types.get(encoder_type, [])]


def get_model_fields(models_path: str, exclude_models: Set[str] = set()) -> dict:
    model_fields = {}
    enabled_models = (config.get_enabled_outputs() if models_path == "api.outputs"
                      else config.get_enabled_inputs() if models_path == "api.inputs"
                      else [])

    for model, model_name in get_models(models_path, exclude_models, enabled_models):
        raw_fields = model.schema().get('properties', {})
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

    properties = model_class.schema().get('properties', {})
    required_fields = model_class.schema().get('required', {})
    parent_fields = {
        "api.outputs": OutputDTO.schema().get('properties', {}),
        "api.inputs": InputDTO.schema().get('properties', {})
    }.get(models_path, {})

    def get_option_name(option):
        if isinstance(option, str):
            return option
        return option.schema().get('properties', {}).get('name', {}).get('default', option.__name__)

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
        if name not in parent_fields or name == "type":
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
            }

            if name in ["video_encoder", "audio_encoder", "mux"]:
                field_type = model_class.__fields__[name].annotation
                allowed_options = []

                if get_origin(field_type) is Union:
                    for arg in get_args(field_type):
                        allowed_options.extend(extract_union_types(arg))
                else:
                    allowed_options.extend(extract_union_types(field_type))

                options = list(dict.fromkeys([get_option_name(option) for option in allowed_options]))

                default_value = None
                default_factory = model_class.__fields__[name].default_factory
                if default_factory:
                    # Get the default value as a string representation
                    default_value = default_factory.__name__.replace('lambda:', '').strip().split('(')[0]
                elif field.get('default') is not None:
                    default_value = get_option_name(field['default'].__class__)

                field_info["options"] = options
                field_info["default"] = default_value

            fields[name] = field_info

    return fields

def get_models(models_path: str, exclude_models: Set[str] = set(), enabled_models: List[str] = None) -> Generator[Tuple[Type[BaseModel], str], None, None]:
    exclude_models.add("BaseModel")
    package_dir = models_path.replace('.', '/')

    for root, _, _ in os.walk(package_dir):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, package_dir).replace(os.sep, '.')
            full_module_name = f"{models_path}.{module_path}.{module_name}" if module_path != '.' else f"{models_path}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and (issubclass(obj, OutputDTO) or issubclass(obj, InputDTO)):
                        model_type = obj.schema().get('properties', {}).get('type', {}).get('default')
                        if not enabled_models or model_type in enabled_models:
                            yield obj, name
            except ModuleNotFoundError as e:
                raise e

def get_dtos(io_type: str) -> Generator[Tuple[Type[BaseModel], str], None, None]:
    base_path = f'api.{io_type}s'
    base_class = InputDTO if io_type == 'input' else OutputDTO

    for _, name, _ in pkgutil.iter_modules([base_path.replace('.', '/')]):
        module = importlib.import_module(f'{base_path}.{name}')
        for attr_name, attr_value in module.__dict__.items():
            if isinstance(attr_value, type) and issubclass(attr_value, base_class) and attr_value != base_class:
                yield attr_value, attr_name.lower().replace(f'{io_type}dto', '')

def get_routers(routes_path: str) -> Generator[Tuple[APIRouter, str], None, None]:
    for root, _, _ in os.walk(routes_path.replace('.', '/')):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, routes_path.replace('.', '/')).replace(os.sep, '.')
            full_module_name = f"{routes_path}.{module_path}.{module_name}" if module_path != '.' else f"{routes_path}.{module_name}"

            module = importlib.import_module(full_module_name)
            if hasattr(module, 'router'):
                yield module.router, module_name


from api.websockets import manager

async def create_preview(handler, type, uid):
    print("CREATE")
    preview_config = config.get_preview_config(type)
    if preview_config['type'] == "hlssink2":
        previewOutput = hlssink2Output(data=hlssink2OutputDTO(
            src=uid,
            is_preview=True,
            ** preview_config
        ))
    elif preview_config['type'] == "srtsink":
        print("SRT!")
        previewOutput = srtsinkOutput(data=srtsinkOutputDTO(
            src=uid,
            is_preview=True,
            uri=f"srt://mediamtx:8890?streamid=publish:{uid}&pkt_size=1316",
            ** preview_config
        ))

    handler.add_pipeline(previewOutput)
    await manager.broadcast("CREATE", previewOutput.data)
    return previewOutput
