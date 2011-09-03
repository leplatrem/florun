#!/usr/bin/python
# -*- coding: utf8 -*-

import logging
import os
import sys
import copy
import codecs
import threading
from xml.dom.minidom import Document, parseString
import tempfile
from gettext import gettext as _
import subprocess
import shlex

import florun
from utils import empty, atoi, traceback2str, plugins_list


logger = logging.getLogger(__name__)


def import_plugins():
    for p in plugins_list(florun.plugins_dirs):
        m = __import__(p)
        globals()[p] = m


class FlowError(Exception):
    pass

class FlowParsingError(FlowError):
    pass

class NodeNotFoundError(FlowError):
    pass


class IncompatibilityError(FlowError):
    """
    Exception when two Node interfaces are incompatible.
    """

    def __init__(self, interface1, interface2):
        super(FlowError, self).__init__(_("%s incompatible with %s") % (interface1.classname, interface2.classname))
        self.interface1 = interface1
        self.interface2 = interface2


class Flow(object):
    """
    Represents a work-flow, in which each L{Node} executes operations.
    """

    def __init__(self, **kwargs):
        self.modified = False
        self.filename = None
        self._nodes = []

    def clone(self):
        return copy.copy(self)

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        self._nodes = nodes

    @property
    def startNodes(self):
        return [n for n in self.nodes if empty(n.predecessors)]

    @property
    def inputNodes(self):
        return [n for n in self.nodes if issubclass(n.__class__, InputNode)]

    def CLIParameterNodes(self):
        return [n for n in self.nodes
                  if issubclass(n.__class__, CommandLineParameterInputNode)]

    def addConnector(self, start, end):
        """
        @type start : {Interface}
        @type end   : {Interface}
        """
        self.modified = True
        if end in start.successors or start in end.successors:
            raise FlowError(_("Connector already exists from %s to %s") % (start, end))
        start.addSuccessor(end)

    def addNode(self, node):
        """
        @param node : L{Node}
        """
        try:
            n = self.findNode(node.id)
            if node.id:
                raise FlowError(_("A node with id '%s' already exists.") % node.id)
            else:
                node.id = self.randomId(node)
        except NodeNotFoundError, e:
            pass
        self.modified = True
        node.flow = self
        self.nodes.append(node)

    def removeConnector(self, start, end):
        """
        @type start : {Interface}
        @type end   : {Interface}
        """
        self.modified = True
        start.removeSuccessor(end)

    def removeNode(self, node):
        """
        @type node : L{Node}
        """
        self.modified = True
        # Remove all connectors
        for interface in node.interfaces:
            for relative in interface.successors:
                self.removeConnector(interface, relative)
            for relative in interface.predecessors:
                self.removeConnector(relative, interface)
        node.flow = None
        # Remove the node itself
        try:
            self.nodes.remove(node)
        except ValueError:
            raise FlowError(_("Node not found in flow."))

    def randomId(self, node):
        """
        Generates a non-existing node id
        @rtype: string
        """
        nodeid = "%s" % node.label
        i = 2
        while nodeid in [n.id for n in self.nodes]:
            nodeid = "%s-%s" % (node.label, i)
            i = i + 1
        return nodeid

    def findNode(self, nodeid):
        """
        Find node by its id
        @rtype: L{Node}
        """
        for n in self.nodes:
            if n.id == nodeid:
                return n
        raise NodeNotFoundError(_("Node with id '%s' not found.") % nodeid)

    @staticmethod
    def load(filename):
        """
        @type filename : string
        @rtype : L{Flow}
        """
        logger.info(_("Load flow from file '%s'") % filename)
        fd = open(filename)
        content = fd.read()
        fd.close()
        f = Flow.importXml(content)
        f.filename = filename
        f.modified = False
        f.sortNodesByIncidence()
        return f

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        # Update incidence field and sort
        self.sortNodesByIncidence()
        xml = self.exportXml()
        logger.info(_("Save flow to file '%s'") % filename)
        fd = open(filename, 'w')
        fd.write(xml)
        fd.close()
        self.modified = False

    def sortNodesByIncidence(self):
        """
        Recursively sets a incidence number for each node,
        depending on its position within the flow.
        Sort nodes on this index.
        """
        def setincidence(nodelist, level):
            for n in nodelist:
                n.incidence = level
                if len(n.successors) > 0:
                    setincidence(n.successors, level + 1)
        setincidence(self.startNodes, 1)
        self.nodes.sort(cmp=lambda x, y: cmp(x.id, y.id))
        self.nodes.sort(cmp=lambda x, y: cmp(x.incidence, y.incidence))

    @classmethod
    def importXml(cls, xmlcontent):
        """
        @type xmlcontent: string
        @rtype: L{Flow}
        """
        flow = Flow()
        dom = parseString(xmlcontent)

        import_plugins()
        for xmlnode in dom.getElementsByTagName('node'):
            nodeid    = xmlnode.getAttribute('id')
            classname = xmlnode.getAttribute('type')
            logger.debug(_(u"XML node type %(classname)s with id '%(nodeid)s'") % locals())

            # Dynamic instanciation of node type
            try:
                classobj = eval(classname)
            except:
                raise FlowParsingError(_(u"Unknown node type '%s'") % classname)

            node = classobj(flow=flow, id=nodeid)

            # Load graphical attributes
            for prop in xmlnode.getElementsByTagName('graphproperty'):
                name  = prop.getAttribute('name')
                value = atoi(prop.getAttribute('value'))
                logger.debug(_(u"XML node property : %s = %s") % (name, value))
                node.graphicalprops[name] = value
            flow.addNode(node)

        # Once all nodes have been loaded, load links :
        for xmlnode in dom.getElementsByTagName('node'):
            nodeid = xmlnode.getAttribute('id')
            node   = flow.findNode(nodeid)
            for xmlinterface in xmlnode.getElementsByTagName('interface'):
                name = xmlinterface.getAttribute('name')
                src  = node.findInterface(name)
                src.slot = True
                if src.isInput() and src.isValue():
                    src.slot = xmlinterface.getAttribute('slot').lower() == 'true'
                    if not src.slot:
                        src.value = xmlinterface.getAttribute('value')
                for xmlsuccessor in xmlinterface.getElementsByTagName('successor'):
                    dnodeid = xmlsuccessor.getAttribute('node')
                    dnode   = flow.findNode(dnodeid)
                    # Find interface on destination node
                    dname = xmlsuccessor.getAttribute('interface')
                    dest  = dnode.findInterface(dname)
                    dest.slot = True
                    src.addSuccessor(dest)
        flow.sortNodesByIncidence()
        return flow

    def exportXml(self):
        """
        @rtype: string
        """
        # Document root
        grxml = Document()
        grxmlr = grxml.createElement('flow')
        grxml.appendChild(grxmlr)
        # Each node...
        for node in self.nodes:
            xmlnode = grxml.createElement('node')
            xmlnode.setAttribute('id', unicode(node.id))
            xmlnode.setAttribute('type', unicode(node.fullname()))
            grxmlr.appendChild(xmlnode)

            # Graphical properties
            if not empty(node.graphicalprops):
                for graphprop in node.graphicalprops:
                    prop = grxml.createElement('graphproperty')
                    prop.setAttribute('name', graphprop)
                    prop.setAttribute('value', "%s" % node.graphicalprops[graphprop])
                    xmlnode.appendChild(prop)

            # Interfaces and successors
            for interface in node.interfaces:
                xmlinterface = grxml.createElement('interface')
                xmlinterface.setAttribute('name', interface.name)
                if interface.isInput() and interface.isValue():
                    xmlinterface.setAttribute('slot', "%s" % interface.slot)
                    if not interface.slot:
                        val = ''
                        if interface.value is not None:
                            val = interface.value
                        xmlinterface.setAttribute('value', "%s" % val)
                if not empty(interface.successors):
                    for successor in interface.successors:
                        xmlsuccessor = grxml.createElement('successor')
                        xmlsuccessor.setAttribute('node', successor.node.id)
                        xmlsuccessor.setAttribute('interface', successor.name)
                        xmlinterface.appendChild(xmlsuccessor)
                xmlnode.appendChild(xmlinterface)

        return grxml.toprettyxml()


class Interface(object):
    """
    Interfaces allow two L{Node}s to be connected.
    """
    PARAMETER, INPUT, RESULT, OUTPUT = range(4)

    def __init__(self, node, name, **kwargs):
        """
        @type node : L{Node}
        @type name : string
        """
        self.node = node
        self.name = name

        #: list of {Interface}
        self.successors = []
        #: list of {Interface}
        self.predecessors = []

        self.type    = kwargs.get('type', self.PARAMETER)
        self.slot    = kwargs.get('slot', True)
        self.default = kwargs.get('default', None)
        self.value   = kwargs.get('value', self.default)
        self.doc     = kwargs.get('doc', '')

        self.__readypredecessors = {}

    def isValue(self):
        return False

    def isInput(self):
        return self.type == self.INPUT or self.type == self.PARAMETER

    def isCompatible(self, other):
        """
        Check whether {self} can be connected to {other}.
        It is necessary in order to check that {self} can load {other}.
        @type other : L{Interface}
        @rtype : boolean
        """
        if self != other and self.node != other.node:
            if self.type != Interface.OUTPUT and other.type != Interface.INPUT:
            # self must be Output, other must be Input
                if self.type != Interface.RESULT and other.type != Interface.PARAMETER:
                # self must be Result, other must be Parameter
                    return True
        return False

    def addSuccessor(self, interface):
        """
        @type interface : L{Interface}
        """
        if not interface.isCompatible(self):
            raise IncompatibilityError(interface, self)
        self.successors.append(interface)
        interface.predecessors.append(self)
        logger.debug(_("%s has following successors : %s") % (self, self.successors))

    def removeSuccessor(self, interface):
        """
        @type interface : L{Interface}
        """
        try:
            self.successors.remove(interface)
            interface.predecessors.remove(self)
        except ValueError:
            raise FlowError(_("Connector does not exist from %s to %s") % (self, interface))

    def load(self, other):
        """
        Method to be overridden by subclasses in order to connect content of nodes interfaces
        @type other : {Interface}
        """
        if other not in self.successors and other not in self.predecessors:
            raise FlowError(_("Should not load interface that is not connected."))
        # Did nothing.

    def clean(self):
        """
        Method to clean and free this interface.
        """
        pass

    def onContentReady(self, interface):
        """
        Receives notifications of predecessors readiness, if all were received, this
        interface is ready. Notify node.
        @type interface: interface whose content is ready.
        """
        self.load(interface)
        self.__readypredecessors[interface] = True
        if len(self.__readypredecessors.keys()) >= len(self.predecessors):
            self.node.debug("All predecessors of %s are ready." % self.fullname)
            self.node.onInterfaceReady(self)

    @property
    def fullname(self):
        """
        @rtype : string
        """
        return u"%s(%s)" % (self.classname, self.name)

    @property
    def classname(self):
        """
        @rtype : string
        """
        return self.__class__.__name__

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return str(unicode(self))

    def __unicode__(self):
        return u"%s::%s" % (self.node, self.fullname)


class Node(object):
    """
    A {Node} is a step in the flow.
    It runs operations, using Parameter {Interface}s, giving Result, reading
    from Input, writing to Output.
    """
    category    = _(u"")
    label       = _(u"")
    description = _(u"")

    def __init__(self, *args, **kwargs):
        self.flow = kwargs.get('flow', None)
        self.id = kwargs.get('id', '')
        if not self.id and self.flow:
            self.id = self.flow.randomId(self)
        self._interfaces = []
        self.incidence   = 0
        self.graphicalprops = {}

        self.__readyinterfaces = {}
        self.canRun  = threading.Event()
        self.running = False

    @classmethod
    def fullname(cls):
        return "%s.%s" % (cls.__module__, cls.__name__)

    def applyAttributes(self, entries):
        """
        @type entries : dict
        """
        for name, tuple in entries.items():
            value, slot = tuple
            if name == 'id':
                self.id = value
            else:
                i = self.findInterface(name)
                i.value = value
                i.slot  = slot
        self.flow.modified = True

    def applyPosition(self, x, y):
        """
        @type x : integer
        @type y : integer
        @return: True if modified.
        """
        # Use other bool, to not interfere with self.flow.modified
        modified = False
        if x != self.graphicalprops.get('x') or y != self.graphicalprops.get('y'):
            modified = True
            self.flow.modified = True
        self.graphicalprops['x'] = x
        self.graphicalprops['y'] = y
        return modified

    @property
    def classname(self):
        """
        @rtype : string
        """
        return self.__class__.__name__

    @property
    def interfaces(self):
        """
        Dynamically list class attributes that are Interfaces.
        @rtype : list of L{Interface}
        """
        if len(self._interfaces) == 0:
            for attr in self.__dict__.values():
                if issubclass(attr.__class__, Interface):
                    self._interfaces.append(attr)
        return self._interfaces

    @property
    def inputInterfaces(self):
        return [i for i in self.interfaces if i.isInput()]

    @property
    def inputSlotInterfaces(self):
        return [i for i in self.inputInterfaces if i.slot]

    @property
    def outputInterfaces(self):
        return [i for i in self.interfaces if not i.isInput()]

    @property
    def successors(self):
        """
        @rtype: list of L{Node}
        """
        successors = []
        for interface in self.interfaces:
            for successor in interface.successors:
                if successor.node not in successors:
                    successors.append(successor.node)
        return successors

    @property
    def predecessors(self):
        """
        @rtype: list of L{Node}
        """
        predecessors = []
        for interface in self.interfaces:
            for predecessor in interface.predecessors:
                if predecessor.node not in predecessors:
                    predecessors.append(predecessor.node)
        return predecessors

    def findInterface(self, name):
        """
        @type name : string
        @rtype : L{Interface}
        """
        for i in self.interfaces:
            if i.name == name:
                return i
        raise FlowError(_("Interface with name '%s' not found on node %s.") % (name, self))

    def onInterfaceReady(self, interface):
        """
        This method keeps track of nodes interfaces that are ready to be loaded.
        When all are ready, execution starts.
        @type interface : L{Interface}
        """
        self.__readyinterfaces[interface] = True
        if len(self.__readyinterfaces.keys()) >= len(self.inputSlotInterfaces):
            # Node has all its input interfaces ready
            self.debug("All interfaces are ready, can start.")
            self.canRun.set()

    def run(self):
        """
        This method is overriden by {Node} subclasses.
        """
        raise NotImplementedError

    def start(self):
        """
        Start execution of node.
        When done, notify successors of this node.
        """
        self.debug(_("Waiting..."))
        self.canRun.wait()
        self.debug(_("Start !"))
        self.running = True

        try:
            self.run()
            self.debug(_("Done."))
        except Exception, e:
            self.exception(e)

        self.running = False
        self.canRun.clear()
        for i in self.outputInterfaces:
            for interface in i.successors:
                self.debug(_("Notify %s") % interface)
                interface.onContentReady(i)

    def clean(self):
        for i in self.interfaces:
            i.clean()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "%s(%s)" % (self.classname, self.id)

    def __unicode__(self):
        return repr(self)

    def debug(self, msg):
        logger.debug(self._logstr(msg))

    def info(self, msg):
        logger.info(self._logstr(msg))

    def error(self, msg):
        logger.error(self._logstr(msg))

    def exception(self, e):
        logger.exception(self._logstr(e))

    def warning(self, msg):
        logger.warning(self._logstr(msg))

    def _logstr(self, msg):
        return u"%s: %s" % (self, msg)


class InterfaceValue(Interface):

    def __init__(self, node, name, **kwargs):
        Interface.__init__(self, node, name, **kwargs)
        self._value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val

    def isValue(self):
        return True

    def isCompatible(self, other):
        if issubclass(other.__class__, InterfaceValue):
            return super(InterfaceValue, self).isCompatible(other)
        return False

    def load(self, other):
        Interface.load(self, other)
        self.value = other.value


class InterfaceStream(Interface):

    def __init__(self, node, name, **kwargs):
        Interface.__init__(self, node, name, **kwargs)
        self.stream = tempfile.NamedTemporaryFile('w+b')

    def __iter__(self):
        return iter(self.stream)

    def clean(self):
        Interface.clean(self)
        self.stream.close()

    def write(self, data):
        self.stream.write(data)

    def flush(self):
        self.stream.flush()

    def isCompatible(self, other):
        if issubclass(other.__class__, InterfaceStream) or \
           issubclass(other.__class__, InterfaceValue)  or \
           issubclass(other.__class__, InterfaceList):
            return super(InterfaceStream, self).isCompatible(other)
        return False

    def load(self, other):
        Interface.load(self, other)
        if issubclass(other.__class__, InterfaceStream):
            #self.stream = copy.copy(other.stream)
            self.stream = codecs.open(other.stream.name, 'rb', 'utf-8')
            #self.stream.seek(0)
        elif issubclass(other.__class__, InterfaceValue):
            self.node.debug(_("Write InterfaceValue to InterfaceStream"))
            ftell = self.stream.tell()
            self.stream.write(u"%s\n" % other.value)
            self.stream.seek(ftell)
        elif issubclass(other.__class__, InterfaceList):
            ftell = self.stream.tell()
            self.node.debug(_("Write InterfaceList to InterfaceStream"))
            self.stream.write(u"\n".join(other.items))
            self.stream.seek(ftell)
        else:
            raise IncompatibilityError(self, other)


class InterfaceList(Interface):

    def __init__(self, node, name, **kwargs):
        Interface.__init__(self, node, name, **kwargs)
        self.items = []

    def __iter__(self):
        return iter(self.items)

    def isCompatible(self, other):
        if issubclass(other.__class__, InterfaceList):
            return super(InterfaceList, self).isCompatible(other)
        return False

    def load(self, other):
        Interface.load(self, other)
        self.items = copy.copy(other.items)


class ProcessNode(Node):
    category = _(u"Basic")
    label    = _(u"Process")
    description = _(u"Execute a shell command")

    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)
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


class InputNode(Node):
    category = _(u"Input")
    label    = _(u"")


class FileInputNode(InputNode):
    label       = _(u"File")
    description = _(u"Read the content of a file")

    def __init__(self, *args, **kwargs):
        InputNode.__init__(self, *args, **kwargs)
        self.filepath = InterfaceValue(self,  'filepath', default='',    type=Interface.PARAMETER, slot=False, doc="file to read")
        self.output   = InterfaceStream(self, 'output',   default='EOF', type=Interface.OUTPUT,    doc="file content")

    def run(self):
        # Read file content and pass to output interface
        if empty(self.filepath.value):
            raise FlowError(_("Filepath empty, cannot read file."))
        self.info(_("Read content of file '%s'") % self.filepath.value)
        f = open(self.filepath.value, 'rb')
        for line in f:
            self.output.write(line)
        self.output.flush()
        f.close()


class ValueInputNode(InputNode):
    label       = _(u"Value")
    description = _(u"A string or number")

    def __init__(self, *args, **kwargs):
        InputNode.__init__(self, *args, **kwargs)
        self.input  = InterfaceValue(self, 'value', default='', type=Interface.PARAMETER, slot=False, doc="Manual value")
        self.output = InterfaceValue(self, 'out', default='',   type=Interface.OUTPUT, doc="value")

    def run(self):
        self.output.value = self.input.value


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
        self.output   = InterfaceStream(self, 'output', default='EOF', type=Interface.OUTPUT, doc="standard input content")

    def run(self):
        for line in sys.stdin:
            self.output.write(line)
        self.output.flush()


class FileListInputNode(InputNode):
    label    = _(u"File list")
    description = _(u"List files of a folder")

    def __init__(self, *args, **kwargs):
        InputNode.__init__(self, *args, **kwargs)
        self.folder   = InterfaceValue(self, 'folder',   default='', type=Interface.PARAMETER, slot=False, doc="folder to scan")
        self.filelist = InterfaceList(self,  'filelist', default='', type=Interface.OUTPUT,    doc="list of file paths")

    def run(self):
        path = self.folder.value
        self.info(_("Recursive file list of folder '%s'") % path)
        self.filelist.items = self.walk(path)

    def walk(self, dirpath):
        filelist = []
        dirpath = os.path.abspath(dirpath)
        if not os.path.exists(dirpath):
            raise FlowError(_("Folder not found '%s'") % dirpath)
        for f in [ff for ff in os.listdir(dirpath) if ff not in [".", ".."]]:
            nfile = os.path.join(dirpath, f)
            filelist.append(nfile)
            if os.path.isdir(nfile):
                filelist.extend(self.walk(nfile))
        return filelist


#
# Output nodes
#


class OutputNode(Node):
    category = _(u"Output")
    label    = _(u"")


class FileOutputNode(OutputNode):
    label    = _(u"File")
    description = _(u"Write the content to a file")

    def __init__(self, *args, **kwargs):
        OutputNode.__init__(self, *args, **kwargs)
        self.filepath = InterfaceValue(self, 'filepath', default='',  type=Interface.PARAMETER, slot=False, doc="file to write")
        self.input    = InterfaceStream(self, 'input', default='EOF', type=Interface.INPUT, doc="input to write")

    def run(self):
        self.info(_("Write content to file '%s'") % self.filepath.value)
        f = open(self.filepath.value, 'wb')
        for line in self.input:
            f.write(line)
        f.close()


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

#
#    Execution classes
#


class NodeRunner(threading.Thread):

    def __init__(self, node):
        threading.Thread.__init__(self)
        self.node = node

    def run(self):
        self.node.start()

    def stop(self):
        pass


class Runner(object):

    def __init__(self, flow):
        self.flow = flow
        self.threads = []

    def start(self):
        logger.info(_("Start execution of flow..."))
        for node in self.flow.nodes:
            th = NodeRunner(node)
            self.threads.append(th)
            th.start()
        # Release semaphores
        logger.debug(_("All node instantiated, waiting for their input interfaces to be ready."))
        for node in self.flow.startNodes:
            node.canRun.set()
        # Wait the end
        logger.debug(_("All input node started. Wait for each node to finish."))
        for th in self.threads:
            th.join()
        # Clean-up
        for n in self.flow.nodes:
            n.clean()
        # Done.
        logger.info(_("Done."))

    def stop(self):
        for th in self.threads:
            th.stop()
