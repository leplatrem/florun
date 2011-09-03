#!/usr/bin/env python
import gzip
from gettext import gettext as _

from florun import flow


"""

    This is a very basic plugin that add support for GZip files.

"""

class FileGZipOutput(flow.FileOutputNode):
    label = _(u"GZip File")
    description = _(u"Write the content to a Gzip file")

    def run(self):
        self.info(_("Write content to file '%s'") % self.filepath.value)
        f = gzip.open(self.filepath.value, 'wb')
        for line in self.input:
            f.write(line)
        f.close()


class FileGZipInput(flow.FileInputNode):
    label = _(u"GZip File")
    description = _(u"Read the content of a Gzip file")

    def run(self):
        self.info(_("Read content of file '%s'") % self.filepath.value)
        f = gzip.open(self.filepath.value, 'rb')
        for line in f:
            self.output.write(line)
        self.output.flush()
        f.close()
