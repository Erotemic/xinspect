__version__ = '0.0.3'

from xinspect import dynamic_kwargs
from xinspect.dynamic_kwargs import get_func_kwargs
from xinspect.autogen import autogen_imports


get_kwargs = get_func_kwargs


__all__ = [
    'dynamic_kwargs',
    'get_func_kwargs',
    'autogen_imports'
]
