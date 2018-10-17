|Travis| |Codecov| |Appveyor| |Pypi|

Tools for static and dynamic code introspection.


Helps with writing doctests

::

    def func(a=1, b=2, c=3):
        """
        Example:
            >>> from this.module import *  # import contextual namespace
            >>> import xinspect
            >>> globals().update(xinspect.get_func_kwargs(func))  # populates globals with default kwarg value
            >>> print(a + b + c)
            6
        """


Helps with code that generates code

::

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


See Also: https://github.com/Erotemic/xdev

  

.. |Travis| image:: https://img.shields.io/travis/Erotemic/xinspect/master.svg?label=Travis%20CI
   :target: https://travis-ci.org/Erotemic/xinspect
.. |Codecov| image:: https://codecov.io/github/Erotemic/xinspect/badge.svg?branch=master&service=github
   :target: https://codecov.io/github/Erotemic/xinspect?branch=master
.. |Appveyor| image:: https://ci.appveyor.com/api/projects/status/github/Erotemic/xinspect?branch=master&svg=True
   :target: https://ci.appveyor.com/project/Erotemic/xinspect/branch/master
.. |Pypi| image:: https://img.shields.io/pypi/v/xinspect.svg
   :target: https://pypi.python.org/pypi/xinspect
