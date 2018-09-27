__version__ = '0.0.2.dev'

from xinspect import dynamic_kwargs
from xinspect.dynamic_kwargs import get_func_kwargs


get_kwargs = get_func_kwargs


__all__ = [
    'dynamic_kwargs',
    'get_func_kwargs',
]
