def auto_argparse(func):
    """
    Transform a function with a Google Style Docstring into an
    `argparse.ArgumentParser`.  Custom utility. Not sure where it goes yet.

    Probably put this in xdev or xinspect?

    Args:
        func ()
    """
    from xdoctest.docstr import docscrape_google as scrape
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
            try:
                argkw['type'] = eval(garg['type'], {})
            except Exception:
                pass
        parser.add_argument('--' + arg, **argkw)
    return parser
