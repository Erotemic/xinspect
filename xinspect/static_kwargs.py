import six
import ast


def parse_kwarg_keys(source, keywords='kwargs', with_vals=False):
    r"""
    Parses the source code to find keys used by the `**kwargs` keywords
    dictionary variable. if `with_vals` is True, we also attempt to infer the
    default values.

    Args:
        source (str):

    Returns:
        list: kwarg_keys

    SeeAlso:
        argparse_funckw
        recursive_parse_kwargs
        parse_kwarg_keys
        parse_func_kwarg_keys
        get_func_kwargs

    Example:
        >>> import ubelt as ub
        >>> source = ub.codeblock(
        >>>    '''
        >>>    x = 'hidden_x'
        >>>    y = 3 # hidden val
        >>>    kwargs.get(x, y)
        >>>    kwargs.get('foo', None)
        >>>    kwargs.pop('bar', 3)
        >>>    kwargs.pop('str', '3fd')
        >>>    kwargs.pop('str', '3f"d')
        >>>    "kwargs.get('baz', None)"
        >>>    kwargs['foo2']
        >>>    #kwargs.get('biz', None)"
        >>>    kwargs['bloop']
        >>>    x = 'bop' in kwargs
        >>>    ''')
        >>> print('source = %s\n' % (source,))
        >>> with_vals = True
        >>> kwarg_items = parse_kwarg_keys(source, with_vals=with_vals)
        >>> result = ('kwarg_items = %s' % (ub.repr2(kwarg_items, nl=1),))
        >>> kwarg_keys = [item[0] for item in kwarg_items]
        >>> assert 'baz' not in kwarg_keys
        >>> assert 'foo' in kwarg_keys
        >>> assert 'bloop' in kwarg_keys
        >>> assert 'bop' not in kwarg_keys
        >>> print(result)
        kwarg_items = [
            ('foo', None),
            ('bar', 3),
            ('str', '3fd'),
            ('str', '3f"d'),
            ('foo2', None),
            ('bloop', None),
        ]
    """
    pt = ast.parse(source)
    kwargs_items = []
    debug = False
    target_kwargs_name = keywords

    if debug:
        import astor
        print('\nInput:')
        print('target_kwargs_name = %r' % (target_kwargs_name,))
        print('\nSource:')
        print(source)
        print('\nParse:')
        print(astor.dump(pt))

    class KwargParseVisitor(ast.NodeVisitor):
        """
        TODO: understand ut.update_existing and dict update
        ie, know when kwargs is passed to these functions and
        then look assume the object that was updated is a dictionary
        and check wherever that is passed to kwargs as well.

        Other visit_<classname> values:
            http://greentreesnakes.readthedocs.io/en/latest/nodes.html
        """
        def __init__(self):
            super(KwargParseVisitor, self).__init__()
            self.const_lookup = {}
            self.first = True

        def visit_FunctionDef(self, node):
            if debug:
                print('VISIT FunctionDef node = %r' % (node,))
                # print('node.args.kwarg = %r' % (node.args.kwarg,))
            if six.PY2:
                kwarg_name = node.args.kwarg
            else:
                if node.args.kwarg is None:
                    kwarg_name = None
                else:
                    kwarg_name = node.args.kwarg.arg

            # Record any constants defined in function definitions
            defaults_vals = node.args.defaults
            offset = len(node.args.args) - len(defaults_vals)
            default_keys = node.args.args[offset:]
            for kwname, kwval in zip(default_keys, defaults_vals):
                # try:
                if six.PY2:
                    if isinstance(kwval, ast.Name):
                        val = eval(kwval.id, {}, {})
                        self.const_lookup[kwname.id] = val
                else:
                    if isinstance(kwval, ast.NameConstant):
                        val = kwval.value
                        self.const_lookup[kwname.arg] = val
                # except Exception:
                #     pass

            if self.first or kwarg_name != target_kwargs_name:
                # target kwargs is still in scope
                ast.NodeVisitor.generic_visit(self, node)
                # always visit the first function
                self.first = False

        def visit_Subscript(self, node):
            if debug:
                print('VISIT SUBSCRIPT node = %r' % (node,))
            if isinstance(node.value, ast.Name):
                if node.value.id == target_kwargs_name:
                    if isinstance(node.slice, ast.Index):
                        index = node.slice
                        key = index.value
                        if isinstance(key, ast.Str):
                            # item = (key.s, None)
                            item = (key.s, None)
                            kwargs_items.append(item)

        @staticmethod
        def _eval_bool_op(val):
            # Can we handle this more intelligently?
            val_value = None
            if isinstance(val.op, ast.Or):
                if any([isinstance(x, ast.NameConstant) and x.value is True for x in val.values]):
                    val_value = True
            elif isinstance(val.op, ast.And):
                if any([isinstance(x, ast.NameConstant) and x.value is False for x in val.values]):
                    val_value = False
            return val_value

        def visit_Call(self, node):
            if debug:
                print('VISIT Call node = %r' % (node,))
                # print(ut.repr4(node.__dict__,))
            if isinstance(node.func, ast.Attribute):
                try:
                    objname = node.func.value.id
                except AttributeError:
                    return
                methodname = node.func.attr
                # funcname = objname + '.' + methodname
                if objname == target_kwargs_name and methodname in {'get', 'pop'}:
                    args = node.args
                    if len(args) == 2:
                        key, val = args
                        if isinstance(key, ast.Name):
                            # TODO lookup constant
                            pass
                        elif isinstance(key, ast.Str):
                            key_value = key.s
                            val_value = None   # ut.NoParam
                            if isinstance(val, ast.Str):
                                val_value = val.s
                            elif isinstance(val, ast.Num):
                                val_value = val.n
                            elif isinstance(val, ast.Name):
                                if val.id == 'None':
                                    val_value = None
                                else:
                                    val_value = self.const_lookup.get(
                                            val.id, None)
                                    # val_value = 'TODO lookup const'
                                    # TODO: lookup constants?
                                    pass
                            elif six.PY3:
                                if isinstance(val, ast.NameConstant):
                                    val_value = val.value
                                elif isinstance(val, ast.Call):
                                    val_value = None
                                elif isinstance(val, ast.BoolOp):
                                    val_value = self._eval_bool_op(val)
                                elif isinstance(val, ast.Dict):
                                    if len(val.keys) == 0:
                                        val_value = {}
                                    else:
                                        val_value = {}
                                    # val_value = callable
                                else:
                                    print('Warning: util_inspect doent know how to parse {}'.format(repr(val)))
                            item = (key_value, val_value)
                            kwargs_items.append(item)
            ast.NodeVisitor.generic_visit(self, node)
    try:
        KwargParseVisitor().visit(pt)
    except Exception:
        raise
        pass
    if with_vals:
        return kwargs_items
    else:
        return [item[0] for item in kwargs_items]

if __name__ == '__main__':
    """
    CommandLine:
        python -m xinspect.static_kwargs all
    """
    import xdoctest
    xdoctest.doctest_module(__file__)
