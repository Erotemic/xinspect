|Codecov| |Pypi| |Downloads| |ReadTheDocs|

Tools for static and dynamic code introspection. This library has not been well
maintained, and there are likely other libraries that are better.


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



.. |CircleCI| image:: https://circleci.com/gh/Erotemic/xinspect.svg?style=svg
    :target: https://circleci.com/gh/Erotemic/xinspect
.. |Codecov| image:: https://codecov.io/github/Erotemic/xinspect/badge.svg?branch=master&service=github
   :target: https://codecov.io/github/Erotemic/xinspect?branch=master
.. |Pypi| image:: https://img.shields.io/pypi/v/xinspect.svg
   :target: https://pypi.python.org/pypi/xinspect
.. |Downloads| image:: https://img.shields.io/pypi/dm/xinspect.svg
   :target: https://pypistats.org/packages/xinspect
.. |ReadTheDocs| image:: https://readthedocs.org/projects/xinspect/badge/?version=latest
    :target: http://xinspect.readthedocs.io/en/latest/
