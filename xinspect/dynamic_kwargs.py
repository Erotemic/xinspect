from __future__ import absolute_import, division, print_function, unicode_literals
import six
import inspect
import re
import types
import ubelt as ub
import textwrap
from xinspect.static_kwargs import parse_kwarg_keys


REGEX_NONGREEDY = '*?'


# THIS IS THE CANNONICAL API FUNCTION. TODO: MAKE OTHER PRIVATE
def get_func_kwargs(func, max_depth=None):
    """
    Dynamically parse the kwargs accepted by this function.

    This function uses Python signatures where possible, but it also uses
    heuristics by inspecting the way any `keywords` dictionary is used.

    Args:
        func (callable): function to introspect kwargs from
        max_depth (int, default=None): by default we recursively parse
            any kwargs passed to subfunctions.
    """
    argspec = get_func_argspec(func)
    if argspec.defaults is None:
        header_kw = {}
    else:
        header_kw = dict(zip(argspec.args[::-1], argspec.defaults[::-1]))
    if argspec.keywords is not None:
        header_kw.update(dict(recursive_parse_kwargs(func, max_depth=max_depth)))
    return header_kw


def bref_field(key):
    """ regex backreference """
    return r'\g<%s>' % (key)


def named_field(key, regex, vim=False):
    """
    Creates a named regex group that can be referend via a backref.
    If key is None the backref is referenced by number.

    References:
        https://docs.python.org/2/library/re.html#regular-expression-syntax
    """
    if key is None:
        #return regex
        return r'(%s)' % (regex,)
    if vim:
        return r'\(%s\)' % (regex)
    else:
        return r'(?P<%s>%s)' % (key, regex)


def is_func_or_method(var):
    return isinstance(var, (types.MethodType, types.FunctionType))


def get_funcglobals(func):
    if six.PY2:
        return getattr(func, 'func_globals')
    else:
        return getattr(func, '__globals__')


def parse_func_kwarg_keys(func, with_vals=False):
    """ hacky inference of kwargs keys

    SeeAlso:
        argparse_funckw
        recursive_parse_kwargs
        parse_kwarg_keys
        parse_func_kwarg_keys
        get_func_kwargs

    """
    sourcecode = get_func_sourcecode(func, strip_docstr=True,
                                     strip_comments=True)
    kwkeys = parse_kwarg_keys(sourcecode, with_vals=with_vals)
    #get_func_kwargs  TODO
    return kwkeys


def get_kwdefaults(func, parse_source=False):
    r"""
    Args:
        func (func):

    Returns:
        dict:

    # CommandLine:
    #     python -m utool.util_inspect get_kwdefaults

    # Example:
    #     >>> # ENABLE_DOCTEST
    #     >>> from utool.util_inspect import *  # NOQA
    #     >>> func = dummy_func
    #     >>> parse_source = True
    #     >>> kwdefaults = get_kwdefaults(func, parse_source)
    #     >>> print('kwdefaults = %s' % (ub.repr2(kwdefaults),))
    """
    argspec = inspect.getargspec(func)
    kwdefaults = {}
    if argspec.args is None or argspec.defaults is None:
        pass
    else:
        args = argspec.args
        defaults = argspec.defaults
        #kwdefaults = OrderedDict(zip(argspec.args[::-1], argspec.defaults[::-1]))
        kwpos = len(args) - len(defaults)
        kwdefaults = ub.odict(zip(args[kwpos:], defaults))
    if parse_source and argspec.keywords:
        # TODO parse for kwargs.get/pop
        keyword_defaults = parse_func_kwarg_keys(func, with_vals=True)
        for key, val in keyword_defaults:
            assert key not in kwdefaults, 'parsing error'
            kwdefaults[key] = val
    return kwdefaults


def lookup_attribute_chain(attrname, namespace):
    """
        >>> attrname = funcname
        >>> namespace = mod.__dict__
        >>> attrname = 'KWReg.print_defaultkw'
    """
    #subdict = meta_util_six.get_funcglobals(root_func)
    subtup = attrname.split('.')
    subdict = namespace
    for attr in subtup[:-1]:
        subdict = subdict[attr].__dict__
    leaf_name = subtup[-1]
    leaf_attr = subdict[leaf_name]
    return leaf_attr


def recursive_parse_kwargs(root_func, path_=None, verbose=None, max_depth=None):
    """
    recursive kwargs parser

    Args:
        root_func (function):  live python function
        path_ (PathLike, default=None):
        max_depth (int, default=None): if specified only recurse to this depth.

    Returns:
        list:

    TODO:
        - [ ] rectify with others
        - [ ] if docstr indentation is off, this fails

    Example:
        >>> modname = ub.argval('--mod', default='ubelt')
        >>> funcname = ub.argval('--func', default='cmd')
        >>> mod = ub.import_module_from_name(modname)
        >>> root_func = lookup_attribute_chain(funcname, mod.__dict__)
        >>> path_ = None
        >>> parsed = recursive_parse_kwargs(root_func)
        >>> flags = ub.unique_flags([p[0] for p in parsed])
        >>> unique = list(ub.compress(parsed, flags))
        >>> print('parsed = %s' % (ub.repr2(parsed),))
        >>> print('unique = %s' % (ub.repr2(unique),))
    """
    if max_depth is None:
        max_depth = float('inf')

    if verbose is None:
        verbose = False
    if verbose:
        print('[inspect] recursive parse kwargs root_func = %r ' % (root_func,))

    if path_ is None:
        path_ = []
    if root_func in path_:
        if verbose:
            print('[inspect] Encountered cycle. returning')
        return []
    path_.append(root_func)
    spec = get_func_argspec(root_func)
    # ADD MORE
    kwargs_list = []
    found_explicit = list(get_kwdefaults(root_func, parse_source=False).items())
    if verbose:
        print('[inspect] * Found explicit %r' % (found_explicit,))

    sourcecode = get_func_sourcecode(root_func, strip_docstr=True,
                                        strip_def=True, strip_decor=True)
    sourcecode1 = get_func_sourcecode(root_func, strip_docstr=True,
                                      strip_def=False, strip_decor=True)
    found_implicit = parse_kwarg_keys(sourcecode1, spec.keywords,
                                         with_vals=True)
    if verbose:
        print('[inspect] * Found found_implicit %r' % (found_implicit,))
    kwargs_list = found_explicit + found_implicit

    def hack_lookup_mod_attrs(attr):
        # HACKS TODO: have find_funcs_called_with_kwargs infer an attribute is a
        # module / function / type. In the module case, we can import it and
        # look it up.  Maybe args, or returns can help infer type.  Maybe just
        # register some known varnames.  Maybe jedi has some better way to do
        # this.
        # if attr == 'ut':
        #     subdict = ut.__dict__
        # elif attr == 'pt':
        #     import plottool as pt
        #     subdict = pt.__dict__
        # else:
        subdict = None
        return subdict

    def resolve_attr_subfunc(subfunc_name):
        # look up attriute chain
        #subdict = root_func.func_globals
        subdict = get_funcglobals(root_func)
        subtup = subfunc_name.split('.')
        try:
            subdict = lookup_attribute_chain(subfunc_name, subdict)
            if is_func_or_method(subdict):
                # Was subdict supposed to be named something else here?
                subfunc = subdict
                return subfunc
        except (KeyError, TypeError):
            for attr in subtup[:-1]:
                try:
                    subdict = subdict[attr].__dict__
                except (KeyError, TypeError):
                    # limited support for class lookup
                    if isinstance(root_func, (types.MethodType,)) and spec.args[0] == attr:
                        subdict = root_func.im_class.__dict__
                    else:
                        # FIXME TODO lookup_attribute_chain
                        subdict = hack_lookup_mod_attrs(attr)
                        if subdict is None:
                            print('Unable to find attribute of attr=%r' % (attr,))
        if subdict is not None:
            attr_name = subtup[-1]
            subfunc = subdict[attr_name]
        else:
            subfunc = None
        return subfunc

    def check_subfunc_name(subfunc_name):
        if isinstance(subfunc_name, tuple) or '.' in subfunc_name:
            subfunc = resolve_attr_subfunc(subfunc_name)
        else:
            # try to directly take func from globals
            func_globals = root_func.__globals__
            try:
                subfunc = func_globals[subfunc_name]
            except KeyError:
                print('Unable to find function definition subfunc_name=%r' %
                      (subfunc_name,))
                subfunc = None
        if subfunc is not None and max_depth > 0:
            subkw_list = recursive_parse_kwargs(subfunc, path_,
                                                verbose=verbose,
                                                max_depth=max_depth - 1)
            new_subkw = subkw_list
        else:
            new_subkw = []
        return new_subkw

    if spec.keywords is not None:
        if verbose:
            print('[inspect] Checking spec.keywords=%r' % (spec.keywords,))
        subfunc_name_list = find_funcs_called_with_kwargs(sourcecode, spec.keywords)
        if verbose:
            print('[inspect] Checking subfunc_name_list=%r' % (subfunc_name_list,))
        for subfunc_name in subfunc_name_list:
            try:
                new_subkw = check_subfunc_name(subfunc_name)
                if verbose:
                    print('[inspect] * Found %r' % (new_subkw,))
                kwargs_list.extend(new_subkw)
            except TypeError:
                print('warning: unable to recursivley parse type of : %r' % (subfunc_name,))
    return kwargs_list


def find_funcs_called_with_kwargs(sourcecode, target_kwargs_name='kwargs'):
    r"""
    Finds functions that are called with the keyword `kwargs` variable

    Example:
        >>> # ENABLE_DOCTEST
        >>> sourcecode = ub.codeblock(
                '''
                x, y = list(zip(*ub.ichunks(data, 2)))
                somecall(arg1, arg2, arg3=4, **kwargs)
                import sys
                sys.badcall(**kwargs)
                def foo():
                    bar(**kwargs)
                    ub.holymoly(**kwargs)
                    baz()
                    def biz(**kwargs):
                        foo2(**kwargs)
                ''')
        >>> child_funcnamess = find_funcs_called_with_kwargs(sourcecode)
        >>> print('child_funcnamess = %r' % (child_funcnamess,))
        >>> assert 'foo2' not in child_funcnamess, 'foo2 should not be found'
        >>> assert 'bar' in child_funcnamess, 'bar should be found'
    """
    import ast
    sourcecode = 'from __future__ import print_function\n' + sourcecode
    pt = ast.parse(sourcecode)
    child_funcnamess = []
    debug = False

    if debug:
        print('\nInput:')
        print('target_kwargs_name = %r' % (target_kwargs_name,))
        print('\nSource:')
        print(sourcecode)
        import astor
        print('\nParse:')
        print(astor.dump(pt))

    class KwargParseVisitor(ast.NodeVisitor):
        """
        TODO: understand dict update ie, know when kwargs is passed to these
        functions and then look assume the object that was updated is a
        dictionary and check wherever that is passed to kwargs as well.
        """
        def visit_FunctionDef(self, node):
            if debug:
                print('\nVISIT FunctionDef node = %r' % (node,))
                print('node.args.kwarg = %r' % (node.args.kwarg,))
            if six.PY2:
                kwarg_name = node.args.kwarg
            else:
                if node.args.kwarg is None:
                    kwarg_name = None
                else:
                    kwarg_name = node.args.kwarg.arg
            if kwarg_name != target_kwargs_name:
                # target kwargs is still in scope
                ast.NodeVisitor.generic_visit(self, node)

        def visit_Call(self, node):
            if debug:
                print('\nVISIT Call node = %r' % (node,))
            if isinstance(node.func, ast.Attribute):
                try:
                    funcname = node.func.value.id + '.' + node.func.attr
                except AttributeError:
                    funcname = None
            elif isinstance(node.func, ast.Name):
                funcname = node.func.id
            else:
                raise NotImplementedError(
                    'do not know how to parse: node.func = %r' % (node.func,))
            if six.PY2:
                kwargs = node.kwargs
                kwargs_name = None if kwargs is None else kwargs.id
                if funcname is not None and kwargs_name == target_kwargs_name:
                    child_funcnamess.append(funcname)
                if debug:
                    print('funcname = %r' % (funcname,))
                    print('kwargs_name = %r' % (kwargs_name,))
            else:
                if node.keywords:
                    for kwargs in node.keywords:
                        if kwargs.arg is None:
                            if hasattr(kwargs.value, 'id'):
                                kwargs_name = kwargs.value.id
                                if funcname is not None and kwargs_name == target_kwargs_name:
                                    child_funcnamess.append(funcname)
                                if debug:
                                    print('funcname = %r' % (funcname,))
                                    print('kwargs_name = %r' % (kwargs_name,))
            ast.NodeVisitor.generic_visit(self, node)
    try:
        KwargParseVisitor().visit(pt)
    except Exception:
        raise
    return child_funcnamess
    #print('child_funcnamess = %r' % (child_funcnamess,))


def get_func_argspec(func):
    """
    wrapper around inspect.getargspec but takes into account utool decorators
    """
    if hasattr(func, '_utinfo'):
        argspec = func._utinfo['orig_argspec']
        return argspec
    if isinstance(func, property):
        func = func.fget
    argspec = inspect.getargspec(func)
    return argspec


def get_func_sourcecode(func, strip_def=False, strip_ret=False,
                        strip_docstr=False, strip_comments=False,
                        remove_linenums=None, strip_decor=False):
    """
    wrapper around inspect.getsource but takes into account utool decorators
    strip flags are very hacky as of now

    Args:
        func (function):
        strip_def (bool):
        strip_ret (bool): (default = False)
        strip_docstr (bool): (default = False)
        strip_comments (bool): (default = False)
        remove_linenums (None): (default = None)

    Example:
        >>> # build test data
        >>> func = get_func_sourcecode
        >>> strip_def = True
        >>> strip_ret = True
        >>> sourcecode = get_func_sourcecode(func, strip_def)
        >>> print('sourcecode = {}'.format(sourcecode))
    """
    inspect.linecache.clearcache()  # HACK: fix inspect bug
    sourcefile = inspect.getsourcefile(func)
    if hasattr(func, '_utinfo'):
        # DEPRICATE
        func2 = func._utinfo['orig_func']
        sourcecode = get_func_sourcecode(func2)
    elif sourcefile is not None and (sourcefile != '<string>'):
        try_limit = 2
        for num_tries in range(try_limit):
            try:
                #print(func)
                sourcecode = inspect.getsource(func)
                if not isinstance(sourcecode, six.text_type):
                    sourcecode = sourcecode.decode('utf-8')
                #print(sourcecode)
            except (IndexError, OSError, SyntaxError) as ex:
                print('WARNING: Error getting source')
                inspect.linecache.clearcache()
                if num_tries + 1 != try_limit:
                    tries_left = try_limit - num_tries - 1
                    print('Attempting %d more time(s)' % (tries_left))
                else:
                    raise
    else:
        sourcecode = None
    if strip_def:
        # hacky
        # TODO: use redbaron or something like that for a more robust appraoch
        sourcecode = textwrap.dedent(sourcecode)
        regex_decor = '^@.' + REGEX_NONGREEDY
        regex_defline = '^def [^:]*\\):\n'
        patern = '(' + regex_decor + ')?' + regex_defline
        RE_FLAGS = re.MULTILINE | re.DOTALL
        RE_KWARGS = {'flags': RE_FLAGS}
        nodef_source = re.sub(patern, '', sourcecode, **RE_KWARGS)
        sourcecode = textwrap.dedent(nodef_source)
        #print(sourcecode)
        pass
    if strip_ret:
        r""" \s is a whitespace char """
        return_ = named_field('return', 'return .*$')
        prereturn = named_field('prereturn', r'^\s*')
        return_bref = bref_field('return')
        prereturn_bref = bref_field('prereturn')
        regex = prereturn + return_
        repl = prereturn_bref + 'pass  # ' + return_bref
        sourcecode_ = re.sub(regex, repl, sourcecode, flags=re.MULTILINE)
        sourcecode = sourcecode_
        pass
    if strip_docstr or strip_comments:
        # pip install pyminifier
        # References: http://code.activestate.com/recipes/576704/
        #from pyminifier import minification, token_utils
        def remove_docstrings_or_comments(source):
            """
            TODO: commit clean version to pyminifier
            """
            import tokenize
            from six.moves import StringIO
            io_obj = StringIO(source)
            out = ''
            prev_toktype = tokenize.INDENT
            last_lineno = -1
            last_col = 0
            for tok in tokenize.generate_tokens(io_obj.readline):
                token_type = tok[0]
                token_string = tok[1]
                start_line, start_col = tok[2]
                end_line, end_col = tok[3]
                if start_line > last_lineno:
                    last_col = 0
                if start_col > last_col:
                    out += (' ' * (start_col - last_col))
                # Remove comments:
                if strip_comments and token_type == tokenize.COMMENT:
                    pass
                elif strip_docstr and token_type == tokenize.STRING:
                    if prev_toktype != tokenize.INDENT:
                        # This is likely a docstring; double-check we're not inside an operator:
                        if prev_toktype != tokenize.NEWLINE:
                            if start_col > 0:
                                out += token_string
                else:
                    out += token_string
                prev_toktype = token_type
                last_col = end_col
                last_lineno = end_line
            return out
        sourcecode = remove_docstrings_or_comments(sourcecode)
        #sourcecode = minification.remove_comments_and_docstrings(sourcecode)
        #tokens = token_utils.listified_tokenizer(sourcecode)
        #minification.remove_comments(tokens)
        #minification.remove_docstrings(tokens)
        #token_utils.untokenize(tokens)

    if strip_decor:
        try:
            import redbaron
            red = redbaron.RedBaron(ub.codeblock(sourcecode))
        except Exception:
            hack_text = ub.ensure_unicode(ub.codeblock(sourcecode)).encode('ascii', 'replace')
            red = redbaron.RedBaron(hack_text)
            pass
        if len(red) == 1:
            redfunc = red[0]
            if redfunc.type == 'def':
                # Remove decorators
                del redfunc.decorators[:]
                sourcecode = redfunc.dumps()

    if remove_linenums is not None:
        source_lines = sourcecode.strip('\n').split('\n')
        delete_items_by_index(source_lines, remove_linenums)
        sourcecode = '\n'.join(source_lines)
    return sourcecode


def delete_items_by_index(list_, index_list, copy=False):
    """
    Remove items from ``list_`` at positions specified in ``index_list``
    The original ``list_`` is preserved if ``copy`` is True

    Args:
        list_ (list):
        index_list (list):
        copy (bool): preserves original list if True

    Example:
        >>> list_ = [8, 1, 8, 1, 6, 6, 3, 4, 4, 5, 6]
        >>> index_list = [2, -1]
        >>> delete_items_by_index(list_, index_list)
        [8, 1, 1, 6, 6, 3, 4, 4, 5]
    """
    if copy:
        list_ = list_[:]
    # Rectify negative indicies
    index_list_ = [(len(list_) + x if x < 0 else x) for x in index_list]
    # Remove largest indicies first
    index_list_ = sorted(index_list_, reverse=True)
    for index in index_list_:
        del list_[index]
    return list_
