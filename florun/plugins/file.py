import os
from gettext import gettext as _

from florun.flow import (FlowError, InputNode, OutputNode,
                         Interface, InterfaceValue, InterfaceStream, InterfaceList)
from florun.utils import empty


"""

    Basic Nodes for reading, writing and listing files

"""

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

