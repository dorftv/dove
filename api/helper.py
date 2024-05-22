import os
import pkgutil
import importlib
from fastapi import APIRouter, Request
from typing import Generator, Tuple, Type, Dict, Set, Any, Optional, Union, List
from api.output_models import OutputDTO
from api.input_models import InputDTO

from pydantic import BaseModel
import json
from pydantic.fields import FieldInfo
#from api.websockets import manager

from config_handler import ConfigReader

config = ConfigReader()


def get_model_fields(models_path: str, exclude_models: Set[str] = set()) -> list:
    model_fields = {}
    enabled_models = []
    if models_path == "api.outputs":
        enabled_models = config.get_enabled_outputs()
    elif models_path == "api.inputs":
        enabled_models = config.get_enabled_inputs()

    models = get_models(models_path, exclude_models, enabled_models)
    for model, model_name in models:
        raw_fields = model.schema().get('properties', None)
        if raw_fields:
            model_type = raw_fields.get('type', {}).get('default')
            if model_type:
                model_fields[model_type] = {
                    "label": model_type,
                    "fields": get_fields(model, models_path)
                }
    if enabled_models:
        model_fields = {k: model_fields[k] for k in enabled_models if k in model_fields}
    return model_fields #sorted_model_fields


def get_fields(model_class: type(BaseModel), models_path: str) -> list:
    fields = {}
    if not issubclass(model_class, BaseModel):
        raise TypeError("Class must be a subclass of pydantic.BaseModel")
    properties = model_class.schema().get('properties', {})
    required_fields = model_class.schema().get('required', {})
    if models_path == "api.outputs":
        parent_fields = OutputDTO.schema().get('properties')
    elif models_path == "api.inputs":
        parent_fields = InputDTO.schema().get('properties')

    for name, field in properties.items():
        if name not in parent_fields or name == "type":
            anyOf = None
            if field.get('anyOf', None) is not None:
                anyOf = field.get('anyOf')[0]['type']
            label = field.get('label', name)
            description = field.get('description', None)
            help = field.get('help', None)
            placeholder = field.get('placeholder', None)
            default = field.get('default', None)
            fields[name] = {
                "name": name,
                "label": label,
                "description": description,
                "help": help,
                "placeholder": placeholder,
                "default": default,
                "type": field.get("type", anyOf),
                "required": name in required_fields,
            }
    return fields


def get_models(models_path: str, exclude_models: Set[str] = set(), enabled_models: str = None) -> Generator[Tuple[Type[BaseModel], str], None, None]:
    exclude_models.add("BaseModel")
    package_dir = models_path.replace('.', '/')
    for root, _, _ in os.walk(package_dir):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, package_dir).replace(os.sep, '.')
            if module_path != '.':
                full_module_name = f"{models_path}.{module_path}.{module_name}"
            else:
                full_module_name = f"{models_path}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)
                for name, obj in module.__dict__.items():
                    skip = False
                    if isinstance(obj, type) and (issubclass(obj, OutputDTO) or issubclass(obj, InputDTO)):# or issubclass(obj, MixerDTO)):
                        raw_fields = obj.schema().get('properties', None)
                        if raw_fields:
                            model_type = raw_fields.get('type', {}).get('default')
                            if not enabled_models:
                                skip = True
                            if model_type and (model_type in enabled_models or skip):
                                print("not")
                                yield obj, name
            except ModuleNotFoundError as e:
                print(f"Module not found: {full_module_name}")
                raise e

# Dynamically load routes from path
def get_routers(routes_path: str) -> Generator[Tuple[APIRouter, str], None, None]:

    package_dir = routes_path.replace('.', '/')

    for root, _, _ in os.walk(package_dir):
        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_path = os.path.relpath(root, package_dir).replace(os.sep, '.')
            if module_path != '.':
                full_module_name = f"{routes_path}.{module_path}.{module_name}"
            else:
                full_module_name = f"{routes_path}.{module_name}"

            module = importlib.import_module(full_module_name)
            if hasattr(module, 'router'):
                yield module.router, module_name



# @TODO: use generic api request handler function
async def handle_request(request: Request, data: BaseModel, OutputClass: Type[BaseModel]):
    handler = request.app.state._state["pipeline_handler"]
    existing_output = None

    data_dict = data.dict()
    output = OutputClass(data=data)

    if hasattr(data, 'uid') and data.uid is not None:
        existing_output = handler.get_pipeline("outputs", data.uid)

    if existing_output is not None:
        existing_output.data = data
    else:
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)
    return data_dict
