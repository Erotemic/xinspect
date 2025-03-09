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
        ...
        >>> print(result)
        kwarg_items = [
            ('foo', None),
            ('bar', 3),
            ('str', '3fd'),
            ('str', '3f"d'),
            ('foo2', None),
            ('bloop', None),
        ]
        >>> assert 'baz' not in kwarg_keys
        >>> assert 'foo' in kwarg_keys
        >>> assert 'bloop' in kwarg_keys
        >>> assert 'bop' not in kwarg_keys
    """
    pt = ast.parse(source)
    kwargs_items = []
    debug = 1
    target_kwargs_name = keywords

    class KwargParseVisitor(ast.NodeVisitor):
        """
        A visitor to parse keyword arguments passed to functions in the AST.

        This will look for functions with kwargs, parse calls to `get` or `pop`,
        and handle constants and expressions as they are found in function signatures.
        """
        def __init__(self):
            super().__init__()
            self.const_lookup = {}
            self.first = True
            self.target_kwargs_name = target_kwargs_name
            self.kwargs_items = kwargs_items

        def visit_FunctionDef(self, node):
            if debug:
                print(f"VISIT FunctionDef node = {node!r}")

            # Get the keyword argument (if any)
            kwarg_name = node.args.kwarg.arg if node.args.kwarg else None

            # Record any constants defined in function definitions
            defaults_vals = node.args.defaults
            offset = len(node.args.args) - len(defaults_vals)
            default_keys = node.args.args[offset:]

            for kwname, kwval in zip(default_keys, defaults_vals):
                if isinstance(kwval, ast.NameConstant):
                    val = kwval.value
                    self.const_lookup[kwname.arg] = val

            # If target kwargs are still in scope, visit the node
            if self.first or kwarg_name != self.target_kwargs_name:
                ast.NodeVisitor.generic_visit(self, node)
                self.first = False

        def visit_Subscript(self, node):
            if debug:
                print(f"VISIT SUBSCRIPT node = {node!r}")
                print(node.value.id)
                print(node.value)
                print(node.slice)

            if isinstance(node.value, ast.Name) and node.value.id == self.target_kwargs_name:
                if isinstance(node.slice, ast.Index):
                    index = node.slice
                    key = index.value
                    if isinstance(key, (ast.Str, ast.Constant)):  # Support both for older and newer Python versions
                        print(f'key={key}')
                        key_value = key.s if isinstance(key, ast.Str) else key.value  # Extract the key's value
                        item = (key_value, None)  # Default value as None
                        self.kwargs_items.append(item)
                elif isinstance(node.slice, ast.Constant):
                    item = (node.slice.value, None)  # Default value as None
                    self.kwargs_items.append(item)

        @staticmethod
        def _eval_bool_op(val):
            val_value = None
            if isinstance(val.op, ast.Or):
                if any(isinstance(x, ast.NameConstant) and x.value is True for x in val.values):
                    val_value = True
            elif isinstance(val.op, ast.And):
                if any(isinstance(x, ast.NameConstant) and x.value is False for x in val.values):
                    val_value = False
            return val_value

        def visit_Call(self, node):
            if debug:
                print(f"VISIT Call node = {node!r}")

            if isinstance(node.func, ast.Attribute):
                try:
                    objname = node.func.value.id
                except AttributeError:
                    return
                methodname = node.func.attr

                if objname == self.target_kwargs_name and methodname in {'get', 'pop'}:
                    args = node.args
                    if len(args) == 2:
                        key, val = args
                        if isinstance(key, ast.Name):
                            pass  # TODO: lookup constant if necessary
                        elif isinstance(key, ast.Str):
                            key_value = key.s
                            val_value = self._parse_value(val)
                            item = (key_value, val_value)
                            self.kwargs_items.append(item)

            ast.NodeVisitor.generic_visit(self, node)

        def _parse_value(self, val):
            """ Helper to parse different types of AST nodes and return their values """
            if isinstance(val, ast.Str):
                return val.s
            elif isinstance(val, ast.Num):
                return val.n
            elif isinstance(val, ast.Name):
                if val.id == 'None':
                    return None
                return self.const_lookup.get(val.id, None)
            elif isinstance(val, ast.NameConstant):
                return val.value
            elif isinstance(val, ast.Call):
                return None  # You can handle Call as necessary
            elif isinstance(val, ast.BoolOp):
                return self._eval_bool_op(val)
            elif isinstance(val, ast.Dict):
                return {}  # You can handle Dict if necessary
            else:
                print(f"Warning: util_inspect doesn't know how to parse {repr(val)}")
                return None

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
