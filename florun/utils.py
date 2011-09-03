#!/usr/bin/python
# -*- coding: utf8 -*-
import os
import cStringIO
import traceback


def empty(data):
    """
    @type data : can be a list, string, dict
    @rtype: boolean
    """
    if data is None:
        return True
    if type(data) == list:
        return len(data) == 0
    if type(data) == dict:
        return len(data.keys()) == 0
    return '%s' % data == ''


def atoi(s):
    """
    Try convert specified string in integer or float,
    and return string otherwise
    """
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            return s


def groupby(list, attribute):
    # Group by category using a hashmap
    groups = {}
    for item in list:
        key = getattr(item, attribute)
        group = groups.get(key, None)
        if group is None:
            groups[key] = []
            group = groups[key]
        group.append(item)
    return groups.values()


def traceback2str(tracebackobj):
    tbinfofile = cStringIO.StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    return tbinfo


def itersubclasses(cls, _seen=None):
    """
    itersubclasses(cls)

    Generator over all subclasses of a given class, in depth first order.
    http://code.activestate.com/recipes/576949/
    """
    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None:
        _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub


def plugins_list(plugins_dirs):
    for path in plugins_dirs.split(os.pathsep):
        for filename in os.listdir(path):
            name, ext = os.path.splitext(filename)
            if ext.endswith(".py"):
                yield name


def import_plugins(plugins_dirs, env):
    for p in plugins_list(plugins_dirs):
        m = __import__(p)
        env[p] = m
