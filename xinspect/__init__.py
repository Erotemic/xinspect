__version__ = '0.2.0'

from xinspect import dynamic_kwargs
from xinspect.dynamic_kwargs import get_func_kwargs
from xinspect.autogen import autogen_imports
from xinspect.auto_argparse import auto_argparse


get_kwargs = get_func_kwargs


__all__ = [
    'auto_argparse',
    'dynamic_kwargs',
    'get_func_kwargs',
    'autogen_imports'
]
