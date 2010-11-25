#!/usr/bin/python
# -*- coding: utf8 -*-

__title__     = "florun"
__author__    = "Mathieu Leplatre"
__email__     = "contact@mathieu-leplatre.info"
__description__ = """Florun allows to graphically design and run workflows."""
__long_description__ = """
By linking basic nodes you can build a whole complex program without writing code !
Like in flow-based programming, you can read, process and write files.
But Florun is extensible ! There could be all kinds of nodes (image, video, Web resources,...) ! 
"""
__url__       = 'http://code.mathieu-leplatre.info/projects/show/florun'
__copyright__ = "Copyright (C) 2009-2010"
__version__   = "0.2.0"
__status__    = "3 - Alpha"
__credits__   = [""]
__license__   = """This is free software, and you are welcome to
redistribute it under certain conditions.
See the GNU General Public Licence for details."""

_          = None
base_dir   = None
locale_dir = ''
icons_dir  = ''


def build_exec_cmd(flow, loglevel, userargs={}):
    """
    @type flow : L{flow.Flow}
    @param loglevel : level from L{utils.Logger}
    @rtype: string
    """
    import os
    florunmain = os.path.join(base_dir, 'florun.py')
    return u'python %s --level %s --execute "%s" %s' % \
                (florunmain,
                 loglevel,
                 flow.filename,
                 " ".join(['--%s "%s"' % (argname, argvalue)
                           for argname, argvalue in userargs.items()]))
