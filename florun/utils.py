import logging

class Logger(object):
    """ Handle and control console and file log output.
    @ivar logger:    the main log handler
    @type logger:    L{logging.logger}
    """
    DEBUG, INFO, WARNING, ERROR = logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)

        console = logging.StreamHandler()
        formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        self.logger.setLevel(self.INFO)
    
    def setLevel(self, level):
        if type(level) != int:
            level = int(level)
        if level < self.DEBUG:
            level = level * 10
        levels = {10:self.DEBUG, 20:self.INFO, 30:self.WARNING, 40:self.ERROR}
        self.logger.setLevel(levels.get(level, self.INFO))

    def logfile(self, filename):
        """ Set logfile output.
        @param filename :    file to write
        @type  filename :    string
        """
        hdlr = logging.FileHandler( filename )
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)

    def debug(self, str):
        self.logger.debug(str)
    def info(self, str):
        self.logger.info(str)
    def warning(self, str):
        self.logger.warning(str)
    def error(self, str):
        self.logger.error(str)

logcore = Logger('florun-core')
loggui  = Logger('florun-ui')

#.......................................................................

def empty(data):
    """
    @type data : can be a list, string, dict
    @rtype: boolean
    """
    if type(data) == list:
        return len(data) == 0
    if type(data) == dict:
        return len(data.keys()) == 0
    if type(data) == str or type(data) == unicode:
        return data == ''
    return data is None

#.......................................................................

def atoi(str):
    """
    Try convert specified string in integer or float, 
    and return string otherwise
    """
    try:
        return int(str)
    except:
        try:
            return float(str)
        except:
            return str


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

#.......................................................................


def itersubclasses(cls, _seen=None):
    """
    itersubclasses(cls)
    
    Generator over all subclasses of a given class, in depth first order.
    http://code.activestate.com/recipes/576949/
    """
    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None: _seen = set()
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

