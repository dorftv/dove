import pkgutil
import importlib
from typing import Type, Generator, Tuple

from dove.pipelines.base import GSTBase

from dove.pipelines.inputs.input import Input
from dove.pipelines.outputs.output import Output



def get_pipeline_classes(io_type: str) -> Generator[Tuple[Type, str], None, None]:
    base_path = f'dove.pipelines.{io_type}s'
    base_class = Input if io_type == 'input' else Output

    for _, name, _ in pkgutil.iter_modules([base_path.replace('.', '/')]):
        module = importlib.import_module(f'{base_path}.{name}')
        for attr_name, attr_value in module.__dict__.items():
            if isinstance(attr_value, type) and issubclass(attr_value, (GSTBase, base_class)) and attr_value not in (GSTBase, base_class):
                yield attr_value, attr_name.lower().replace(io_type, '')
