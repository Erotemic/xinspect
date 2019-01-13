def auto_argparse(func):
    """
    Transform a function with a Google Style Docstring into an
    `argparse.ArgumentParser`.

    TODO:
        - [ ] Handle booleans consistently, allow --flag=True and --flag=False

    Args:
        func (callable): function with kwargs
    """
    from xdoctest.docstr import docscrape_google as scrape
    import ast
    import argparse
    import ubelt as ub
    import inspect
    spec = inspect.getargspec(func)

    # Parse default values from the function dynamically
    try:
        import xinspect
        kwdefaults = xinspect.get_func_kwargs(func)
    except Exception as ex:
        raise
        kwdefaults = dict(zip(spec.args[-len(spec.defaults):], spec.defaults))

    # Parse help and description information from a google-style docstring
    docstr = func.__doc__
    description = scrape.split_google_docblocks(docstr)[0][1][0].strip()

    # TODO: allow scraping from the kwargs block as well
    google_args = {argdict['name']: argdict
                   for argdict in scrape.parse_google_args(docstr)}

    argnames = ub.oset(spec.args) | ub.oset(kwdefaults)
    argnames = (ub.oset(google_args) & argnames) | argnames

    # DEBUG = 1
    # if DEBUG:
    #     print(ub.repr2(google_args))

    # Create the argument parser and register each argument
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    for arg in argnames:
        argkw = {}
        if arg in kwdefaults:
            argkw['default'] = kwdefaults[arg]
        if arg in google_args:
            garg = google_args[arg]
            argkw['help'] = garg['desc']
            # print('-----')
            # print('argkw = {}, {}'.format(arg, ub.repr2(argkw)))
            try:
                if garg['type'] == 'PathLike':
                    argkw['type'] = str
                elif garg['type'] == 'bool':
                    def _parse_bool(s):
                        return bool(ast.literal_eval(s))
                    argkw['type'] = _parse_bool
                else:
                    argkw['type'] = eval(garg['type'], {})
                    # literal_eval doesnt handle types
                    # argkw['type'] = ast.literal_eval(garg['type'])
            except Exception as ex:
                # print('{}, ex = {!r}'.format(arg, ex))
                pass
        # print('-----')
        # print('argkw = {}, {!r}'.format(arg, argkw))
        parser.add_argument('--' + arg, **argkw)
    return parser
