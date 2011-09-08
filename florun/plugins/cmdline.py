import sys
import subprocess
import shlex
from gettext import gettext as _

from florun.flow import (FlowError, InputNode, OutputNode, ProcessNode,
                         Interface, InterfaceValue, InterfaceStream)
from florun.utils import empty


"""

    Basic Nodes for interacting with Command-line

"""

class ShellProcessNode(ProcessNode):
    category = _(u"Basic")
    label    = _(u"Shell Process")
    description = _(u"Execute a shell command")

    def __init__(self, *args, **kwargs):
        super(ShellProcessNode, self).__init__(*args, **kwargs)
        self.stdin   = InterfaceStream(self, 'stdin',  default='EOF', type=Interface.INPUT,  doc="standard input")
        self.stdout  = InterfaceStream(self, 'stdout', default='EOF', type=Interface.OUTPUT, doc="standard output")
        self.stderr  = InterfaceStream(self, 'stderr', default='EOF', type=Interface.OUTPUT, doc="standard error output")
        self.command = InterfaceValue(self,  'cmd',    default='',    type=Interface.PARAMETER, slot=False, doc="command to run")
        self.result  = InterfaceValue(self,  'result', default=0,     type=Interface.RESULT, doc="execution code return")

    def run(self):
        # Run cmd with input from stdin, and send output to stdout/stderr, result code
        cmd = str(self.command.value)
        args = shlex.split(cmd)
        self.info("Run command '%s'" % args)
        proc = subprocess.Popen(args, stdin=self.stdin.stream, stdout=self.stdout.stream, stderr=self.stderr.stream)
        proc.wait()
        self.result.value = proc.returncode


class CommandLineParameterInputNode(InputNode):
    label       = _(u"CLI Param")
    description = _(u"Read a Command-Line Interface parameter")

    def __init__(self, *args, **kwargs):
        InputNode.__init__(self, *args, **kwargs)
        self.name    = InterfaceValue(self, 'name',    default='', type=Interface.PARAMETER, slot=False, doc=_("Command line interface parameter name"))
        self.value   = InterfaceValue(self, 'value',   default='', type=Interface.OUTPUT,    doc=_("value retrieved"))
        self.default = InterfaceValue(self, 'default', default='', type=Interface.PARAMETER, slot=False, doc=_("default value if not specified at runtime"))

        #: L{optparse.Values}
        self.options = None

    def isCLIParameterNode(self):
        return True

    def run(self):
        # Options were parsed in main
        value = getattr(self.options, self.paramname)
        if empty(value):
            self.debug("Expected parameter '%s' is missing from command-line, use default." % self.paramname)
            value = self.default.value
        self.info(_("CLI Parameter '%s'='%s'") % (self.paramname, value))
        self.value.value = value

    @property
    def paramname(self):
        name = self.name.value
        if empty(name):
            raise FlowError(_("Error in getting name of CLI Parameter"))
        return name


class CommandLineStdinInputNode(InputNode):
    label    = _(u"CLI Stdin")
    description = _(u"Read the Command-Line Interface standard input")

    def __init__(self, *args, **kwargs):
        InputNode.__init__(self, *args, **kwargs)
        self.output = InterfaceStream(self, 'output', default='EOF', type=Interface.OUTPUT, doc="standard input content")

    def run(self):
        for line in sys.stdin:
            self.output.write(line)
        self.output.flush()



class CommandLineStdoutOutputNode(OutputNode):
    label       = _(u"CLI Stdout")
    description = _(u"Write to the Command-Line Interface standard output")

    def __init__(self, *args, **kwargs):
        OutputNode.__init__(self, *args, **kwargs)
        self.outstream = sys.stdout
        self.input     = InterfaceStream(self, 'input', default='EOF', type=Interface.INPUT, doc="standard output")

    def run(self):
        for line in self.input:
            self.outstream.write(line)
        self.outstream.flush()
