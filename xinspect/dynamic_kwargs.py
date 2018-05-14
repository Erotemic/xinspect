import six
import inspect
import re
import types
from xinspect.static_kwargs import parse_kwarg_keys


def lookup_attribute_chain(attrname, namespace):
    """
        >>> attrname = funcname
        >>> namespace = mod.__dict__


        >>> import utool as ut
        >>> globals_ = ut.util_inspect.__dict__
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


def recursive_parse_kwargs(root_func, path_=None, verbose=None):
    """
    recursive kwargs parser
    TODO: rectify with others
    FIXME: if docstr indentation is off, this fails

    Args:
        root_func (function):  live python function
        path_ (None): (default = None)

    Returns:
        list:

    CommandLine:
        python -m utool.util_inspect recursive_parse_kwargs:0
        python -m utool.util_inspect recursive_parse_kwargs:0 --verbinspect
        python -m utool.util_inspect recursive_parse_kwargs:1
        python -m utool.util_inspect recursive_parse_kwargs:2 --mod plottool --func draw_histogram

        python -m utool.util_inspect recursive_parse_kwargs:2 --mod vtool --func ScoreNormalizer.visualize

        python -m utool.util_inspect recursive_parse_kwargs:2 --mod ibeis.viz.viz_matches --func show_name_matches --verbinspect
        python -m utool.util_inspect recursive_parse_kwargs:2 --mod ibeis.expt.experiment_drawing --func draw_rank_cmc --verbinspect

    Example:
        >>> # ENABLE_DOCTEST
        >>> from utool.util_inspect import *  # NOQA
        >>> import utool as ut
        >>> root_func = iter_module_doctestable
        >>> path_ = None
        >>> result = ut.repr2(recursive_parse_kwargs(root_func), nl=1)
        >>> print(result)
        [
            ('include_funcs', True),
            ('include_classes', True),
            ('include_methods', True),
            ('include_builtin', True),
            ('include_inherited', False),
            ('debug_key', None),
        ]

    Example:
        >>> # DISABLE_DOCTEST
        >>> from utool.util_inspect import *  # NOQA
        >>> from ibeis.algo.hots import chip_match
        >>> root_func = chip_match.ChipMatch.show_ranked_matches
        >>> path_ = None
        >>> result = ut.repr2(recursive_parse_kwargs(root_func))
        >>> print(result)

    Example:
        >>> import ubelt as ub
        >>> modname = ub.argval('--mod', default='plottool')
        >>> funcname = ub.argval('--func', default='draw_histogram')
        >>> mod = ut.import_modname(modname)
        >>> root_func = lookup_attribute_chain(funcname, mod.__dict__)
        >>> path_ = None
        >>> parsed = recursive_parse_kwargs(root_func)
        >>> flags = ut.unique_flags(ut.take_column(parsed, 0))
        >>> unique = ut.compress(parsed, flags)
        >>> print('parsed = %s' % (ut.repr4(parsed),))
        >>> print('unique = %s' % (ut.repr4(unique),))
    """
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
    found_explicit = list(ut.get_kwdefaults(root_func, parse_source=False).items())
    if verbose:
        print('[inspect] * Found explicit %r' % (found_explicit,))

    #kwargs_list = [(kw,) for kw in  ut.get_kwargs(root_func)[0]]
    sourcecode = get_func_sourcecode(root_func, strip_docstr=True,
                                        stripdef=True)
    sourcecode1 = get_func_sourcecode(root_func, strip_docstr=True,
                                         stripdef=False)
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
        if attr == 'ut':
            subdict = ut.__dict__
        elif attr == 'pt':
            import plottool as pt
            subdict = pt.__dict__
        else:
            subdict = None
        return subdict

    def resolve_attr_subfunc(subfunc_name):
        # look up attriute chain
        #subdict = root_func.func_globals
        subdict = meta_util_six.get_funcglobals(root_func)
        subtup = subfunc_name.split('.')
        try:
            subdict = lookup_attribute_chain(subfunc_name, subdict)
            if ut.is_func_or_method(subdict):
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
        if subfunc is not None:
            subkw_list = recursive_parse_kwargs(subfunc, path_, verbose=verbose)
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
        >>> import ubelt as ub
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
        TODO: understand ut.update_existing and dict update
        ie, know when kwargs is passed to these functions and
        then look assume the object that was updated is a dictionary
        and check wherever that is passed to kwargs as well.
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


def get_func_kwargs(func, recursive=True):
    argspec = get_func_argspec(func)
    if argspec.defaults is None:
        header_kw = {}
    else:
        header_kw = dict(zip(argspec.args[::-1], argspec.defaults[::-1]))
    if argspec.keywords is not None:
        header_kw.update(dict(recursive_parse_kwargs(func)))
    return header_kw


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


def get_func_sourcecode(func, stripdef=False, stripret=False,
                        strip_docstr=False, strip_comments=False,
                        remove_linenums=None):
    """
    wrapper around inspect.getsource but takes into account utool decorators
    strip flags are very hacky as of now

    Args:
        func (function):
        stripdef (bool):
        stripret (bool): (default = False)
        strip_docstr (bool): (default = False)
        strip_comments (bool): (default = False)
        remove_linenums (None): (default = None)

    Example:
        >>> # build test data
        >>> func = get_func_sourcecode
        >>> stripdef = True
        >>> stripret = True
        >>> sourcecode = get_func_sourcecode(func, stripdef)
        >>> # verify results
        >>> print(result)
    """
    import utool as ut
    #try:
    inspect.linecache.clearcache()  # HACK: fix inspect bug
    sourcefile = inspect.getsourcefile(func)
    #except IOError:
    #    sourcefile = None
    if hasattr(func, '_utinfo'):
        #if 'src' in func._utinfo:
        #    sourcecode = func._utinfo['src']
        #else:
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
    #orig_source = sourcecode
    #print(orig_source)
    if stripdef:
        # hacky
        sourcecode = ut.unindent(sourcecode)
        #sourcecode = ut.unindent(ut.regex_replace('def [^)]*\\):\n', '', sourcecode))
        #nodef_source = ut.regex_replace('def [^:]*\\):\n', '', sourcecode)
        regex_decor = '^@.' + ut.REGEX_NONGREEDY
        regex_defline = '^def [^:]*\\):\n'
        patern = '(' + regex_decor + ')?' + regex_defline
        nodef_source = ut.regex_replace(patern, '', sourcecode)
        sourcecode = ut.unindent(nodef_source)
        #print(sourcecode)
        pass
    if stripret:
        r""" \s is a whitespace char """
        return_ = ut.named_field('return', 'return .*$')
        prereturn = ut.named_field('prereturn', r'^\s*')
        return_bref = ut.bref_field('return')
        prereturn_bref = ut.bref_field('prereturn')
        regex = prereturn + return_
        repl = prereturn_bref + 'pass  # ' + return_bref
        #import re
        #print(re.search(regex, sourcecode, flags=re.MULTILINE ))
        #print(re.search('return', sourcecode, flags=re.MULTILINE | re.DOTALL ))
        #print(re.search(regex, sourcecode))
        sourcecode_ = re.sub(regex, repl, sourcecode, flags=re.MULTILINE)
        #print(sourcecode_)
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

    if remove_linenums is not None:
        source_lines = sourcecode.strip('\n').split('\n')
        ut.delete_items_by_index(source_lines, remove_linenums)
        sourcecode = '\n'.join(source_lines)
    return sourcecode
