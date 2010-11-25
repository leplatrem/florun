#!/usr/bin/python
# -*- coding: utf8 -*-
import logging
import os
import sys
from optparse import OptionParser
import gettext

import florun
import florun.gui
import florun.flow
from florun.flow import FlowException


def showversion():
    print _("""%(__title__)s version %(__version__)s
%(__copyright__)s by %(__author__)s, %(__credits__)s

%(__license__)s""") % florun.__dict__


def main(prefix):
    if not prefix.startswith('/usr'):
        florun.base_dir   = prefix
        florun.locale_dir = os.path.join(prefix, 'florun', 'locale')
        florun.icons_dir  = os.path.join(prefix, 'florun', 'icons')
    else:
        prefix = os.path.join(prefix, '..')
        prefix = os.path.abspath(os.path.normpath(prefix))
        florun.base_dir   = os.path.expanduser("~")
        florun.locale_dir = os.path.join(prefix, 'share', 'locale')
        florun.icons_dir  = os.path.join(prefix, 'share', 'florun', 'icons')

    # Set up the path to translation files
    gettext.install('florun', florun.locale_dir, unicode=True)
    florun._ = _

    # Parse command-line arguments
    parser = OptionParser(usage='%s [options]' % florun.__title__)

    parser.add_option("-v", "--version",
                      dest="version", default=False, action="store_true",
                      help=_("Show version"))
    parser.add_option("-e", "--edit",
                      dest="edit", default=None,
                      help=_("Edit specified Florun file"))
    parser.add_option("-x", "--execute",
                      dest="execute", default=None,
                      help=_("Execute specified Florun file"))
    parser.add_option("-l", "--level",
                      dest="level", default=logging.DEBUG, type='int',
                      help=_("Logging level for messages (1:debug 2:info, 3:warning, 4:errors, 5:critical)"))

    # We distinguish official args from args passed to flow
    args = sys.argv[1:]
    last = len(args)
    for i, arg in enumerate(args):
        if arg.startswith('-') and parser.get_option(arg) is None:
            last = i
            break
    # Parse only first part of args
    (options, useless) = parser.parse_args(args[:last])

    logging.basicConfig()
    florun.flow.logger.setLevel(options.level)
    florun.gui.logger.setLevel(options.level)

    if options.version:
        showversion()
        return 0

    florun.gui.logger.debug("Prefix : '%s'" % prefix)
    florun.gui.logger.debug("Icons  : '%s'" % florun.icons_dir)

    if options.edit is not None:
        # Run editor on specified flow
        return florun.gui.main(args, options.edit)
    elif options.execute is not None:
        try:
            # Load flow definition
            wf = florun.flow.Flow.load(options.execute)
            # Check if flow uses cmd line args
            cmdparamnodes = wf.CLIParameterNodes()
            if len(cmdparamnodes) > 0:
                # Parse the rest of args
                parser = OptionParser()
                for node in cmdparamnodes:
                    parser.add_option("-%s" % node.paramname[:1],
                                      "--%s" % node.paramname,
                                      dest=node.paramname)
                (options, parsedargs) = parser.parse_args(args[last:])
                for node in cmdparamnodes:
                    node.options = options
            runner = florun.flow.Runner(wf)
            runner.start()
        except FlowException, e:
            florun.flow.logger.exception(e)
            return 1
        except KeyboardInterrupt, e:
            florun.flow.logger.error(_("Interrupted by user"))
            return 2
    else:
        return florun.gui.main(args)
    return 0


if __name__ == "__main__":
    # Paths
    florun_script = sys.argv[0]
    if os.path.islink(florun_script):
        florun_script = os.readlink(florun_script)
    prefix = os.path.dirname(florun_script)
    code = main(prefix)
    florun.flow.logger.info(florun._("Exit. (status=%s)") % code)
    sys.exit(code)
