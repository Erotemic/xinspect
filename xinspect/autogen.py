from __future__ import absolute_import, division, print_function, unicode_literals
import os
import warnings
import tempfile
import collections
from collections import OrderedDict


def undefined_names(fpath=None, source=None):
    """
    Use a linter to find undefined names in a Python file

    Args:
        fpath (PathLike): path to the file
        source (str): source code of file (mutually exclusive with fpath)

    Example:
        >>> import ubelt as ub
        >>> source = ub.codeblock(
        >>>     '''
        >>>     p = os.path.dirname(join('a', 'b'))
        >>>     glob.glob(p)
        >>>     ''')
        >>> sorted(undefined_names(source=source))
        ['glob', 'join', 'os']
    """
    import pyflakes.api
    import pyflakes.reporter

    if not (bool(source) ^ bool(fpath)):
        raise ValueError('Must specify exactly one fpath or source')

    class CaptureReporter(pyflakes.reporter.Reporter):
        def __init__(reporter, warningStream, errorStream):
            reporter.syntax_errors = []
            reporter.messages = []
            reporter.unexpected = []

        def unexpectedError(reporter, filename, msg):
            reporter.unexpected.append(msg)

        def syntaxError(reporter, filename, msg, lineno, offset, text):
            reporter.syntax_errors.append(msg)

        def flake(reporter, message):
            reporter.messages.append(message)

    # TODO: use code transformer to remove import * by default

    if source is not None:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py')
        tmp.file.write(source)
        tmp.file.flush()
        fpath = tmp.name

    names = set()
    reporter = CaptureReporter(None, None)
    pyflakes.api.checkPath(fpath, reporter)
    for msg in reporter.messages:
        if msg.__class__.__name__.endswith('UndefinedName'):
            assert len(msg.message_args) == 1
            names.add(msg.message_args[0])
    return names


class Importables(object):
    """
    Class that keeps track of registered known importables
    """
    def __init__(self, default=None):
        # A mapping from undefined names in a file to the appropriate line of
        # Python code that defines that name (usually an import)
        if default is None:
            default = OrderedDict()
        elif isinstance(default, Importables) or hasattr(default, 'known'):
            default = default.known
        self.known = default

    def update(self, other):
        self.known.update(other)

    def __getitem__(self, key):
        return self.known[key]

    def __iter__(self):
        return iter(self.known)

    def _use_recommended_defaults(self):
        """
        Adds a list of default values that I like.
        This should change to be much more configurable.
        """
        self._populate_common_modules()
        self._populate_common_aliases()
        self._populate_uncommon_aliases()
        self._populate_ubiquitous_stdlib_members()

    def _populate_common_modules(self):
        modules = [
            'cv2', 'glob', 'torch', 'math'
        ]
        for name in modules:
            self.known[name] = 'import {}'.format(name)

    def _populate_common_aliases(self):
        self.known.update({
            'np': 'import numpy as np',
            'pd': 'import pandas as pd',
            'mpl': 'import matplotlib as mpl',
        })

    def _populate_uncommon_aliases(self):
        self.known.update({
            'it': 'import itertools as it',
            'nn': 'from torch import nn',
            'F': 'import torch.nn.functional as F',
            'Image': 'from PIL import Image',
            'ub': 'import ubelt as ub',
            'nh': 'import netharn as nh',
        })

    def _populate_ubiquitous_stdlib_members(self):
        # Add os.path members to aliased importables
        for name in dir(os.path):
            if not name.startswith('_') and name != 'os':
                self.known[name] = 'from os.path import {}'.format(name)
        for key in collections.__all__:
            self.known[key] = 'from collections import {}'.format(key)

        # Note: not all ctypes members are ubuquitous
        # ctypes_members = [d for d in dir(ctypes) if not d.startswith('_')]
        ctypes_members = [
            'c_bool', 'c_buffer', 'c_byte', 'c_char', 'c_char_p', 'c_double',
            'c_float', 'c_int', 'c_int16', 'c_int32', 'c_int64', 'c_int8',
            'c_long', 'c_longdouble', 'c_longlong', 'c_short', 'c_size_t',
            'c_ssize_t', 'c_ubyte', 'c_uint', 'c_uint16', 'c_uint32',
            'c_uint64', 'c_uint8', 'c_ulong', 'c_ulonglong', 'c_ushort',
            'c_void_p', 'c_voidp', 'c_wchar', 'c_wchar_p',
            'ARRAY', 'BigEndianStructure', 'CDLL', 'CFUNCTYPE', 'DEFAULT_MODE',
            'LibraryLoader', 'LittleEndianStructure', 'POINTER', 'PYFUNCTYPE',
            'PyDLL', 'RTLD_GLOBAL', 'RTLD_LOCAL', 'SetPointerType',
            'addressof', 'byref', 'cast', 'pointer',
        ]
        for key in ctypes_members:
            self.known[key] = 'from ctypes import {}'.format(key)

    def _populate_existing_modnames(self, names):
        # Populates any name that corresponds to a top-level module
        from xdoctest import static_analysis as static
        for n in names:
            if n not in self.known:
                if static.modname_to_modpath(n) is not None:
                    self.known[n] = 'import {}'.format(n)


def autogen_imports(fpath=None, source=None, importable=None,
                    search_modnames=True):
    """
    Generate lines of code that would fix the undefined names.

    This will work out of the box for common aliases (e.g. np) and for names
    that correspond to top-level modules, but anything else will require
    external hints to be passed in via importable.

    Args:
        fpath (PathLike): path to the module in question

        source (str): source code of file (mutually exclusive with fpath)

        importable (dict | Importables): mapping from names to import lines

        search_modnames (bool): if True, searches PYTHONPATH for existing
            modnames that match undefined unknown names.

    Example:
        >>> import ubelt as ub
        >>> source = ub.codeblock(
        >>>     '''
        >>>     p = os.path.dirname(join('a', 'b'))
        >>>     glob.glob(p)
        >>>     ''')
        >>> # Generate a list of lines to fix the name errors
        >>> lines = autogen_imports(source=source)
        >>> print(lines)
        ['import glob', 'from os.path import join', 'import os']
        >>> # After fixing the errors, the file does not need modification
        >>> newsource = chr(10).join(lines) + chr(10) + source
        >>> newlines = autogen_imports(source=newsource)
        >>> print(newlines)
        []
    """

    if not (bool(source) ^ bool(fpath)):
        raise ValueError('Must specify exactly one fpath or source')

    # Search for undefined names in a module
    names = undefined_names(fpath, source=source)

    # Use predefined
    if importable is None:
        importable = Importables()
        importable._use_recommended_defaults()

    importable = Importables(importable)
    if search_modnames:
        importable._populate_existing_modnames(names)

    # Add any unregistered names if they correspond with a findable module
    have_names = set(importable.known).intersection(set(names))
    missing = set(names) - set(have_names)
    if missing:
        message = ('Warning: unknown modules {}'.format(missing))
        print(message)
        warnings.warn(message)

    import_lines = [importable.known[n] for n in sorted(have_names)]
    return import_lines

