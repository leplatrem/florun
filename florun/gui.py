#!/usr/bin/python
import os, sys
import cStringIO, traceback

from PyQt4.QtCore import *
from PyQt4.QtGui  import QDesktopWidget, QApplication, QMainWindow, QIcon, QFileDialog, QAction, QStyle, QWidget, QFrame, QLabel, QTabWidget, QLineEdit, QTextEdit, QPushButton, QToolBox, QGroupBox, QCheckBox, QComboBox, QSplitter, QGridLayout, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsItemGroup, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QDrag, QPainter, QColor, QFont, QPen, QPixmap 
from PyQt4.QtSvg  import QGraphicsSvgItem

import florun
from florun.flow  import *
from florun.utils import logcore, loggui, itersubclasses, groupby, empty

"""

   Diagram items

"""
class SlotItem(QGraphicsEllipseItem):
    """
    A {SlotItem} is the graphical representation of a {flow.Interface}.
    """
    SIZE = 12
    COLORS = {InterfaceValue :QColor(255,255,64), 
              InterfaceStream:QColor(255,159,64),
              InterfaceList  :QColor(159,255,64),}
    TEXT_LEFT, TEXT_RIGHT, TEXT_BOTTOM, TEXT_TOP = range(4)
    
    def __init__(self, parent, interface, textposition = None):
        QGraphicsEllipseItem.__init__(self, parent)
        self.parent = parent
        self.connectors = []
        # Underlying object
        self.interface = interface
        self.buildItem()
        self.highlight = False
        self.text.setPlainText(interface.name)
        if textposition is None:
            textposition = SlotItem.TEXT_RIGHT
        self.textposition = textposition

    def buildItem(self):
        color = self.COLORS.values()[0]
        for iclass, icolor in self.COLORS.items():
            if issubclass(self.interface.__class__, iclass):
                color = icolor
        self.setBrush(color)
        self.setZValue(self.parent.zValue() + 1)
        self.text = QGraphicsTextItem(self)
        self.text.setParentItem(self)
        f = QFont()
        f.setPointSize(6)
        self.text.setFont(f)

    def setPos(self, pos):
        #QGraphicsEllipseItem.setPos(self, pos)
        self.setRect(pos.x(), pos.y(), self.SIZE, self.SIZE)
        self.text.setPos(pos + self.textOffset())
        self.update()

    @property
    def label(self):
        return self.interface.name

    @property
    def highlight(self):
        return self._highlight
    
    @highlight.setter
    def highlight(self, state):
        self._highlight = state
        if state:
            self.setPen(QPen(Qt.darkMagenta, 3))
        else:
            if len(self.connectors) == 0:
                self.setPen(QPen(Qt.darkGray, 2))
            else:
                self.setPen(QPen(Qt.darkMagenta, 2))

    def connect(self, connector, start = True):
        if start:
            connector.startItem = self
        else:
            connector.endItem = self
        self.connectors.append(connector)
        self.highlight = True

    def disconnect(self, connector):
        self.connectors.remove(connector)
        self.highlight = len(self.connectors) > 0

    def textOffset(self):
        textrect = self.text.boundingRect()
        x = y = 0
        if self.textposition == SlotItem.TEXT_TOP:
            x = x - textrect.width()/2 + self.SIZE/2
            y = y - self.SIZE - 2
        elif self.textposition == SlotItem.TEXT_BOTTOM:
            x = x - textrect.width()/2 + self.SIZE/2
            y = y + self.SIZE
        elif self.textposition == SlotItem.TEXT_LEFT:
            x = x - textrect.width()
            y = y - textrect.height()/4
        elif self.textposition == SlotItem.TEXT_RIGHT:
            x = x + self.SIZE
            y = y - textrect.height()/4
        return QPointF(x, y)

    def __unicode__(self):
        return u"%s:%s (%s)" % (self.parent, self.label, len(self.connectors))



class DiagramConnector(QGraphicsLineItem):
    """
    A {DiagramConnector} is a visual representation of an {flow.Interface}s successor.
    """
    def __init__(self, *args):
        QGraphicsLineItem.__init__(self, *args)
        self.setPen(QPen(Qt.darkMagenta, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.setAcceptHoverEvents(True)
        self.setZValue(-1000)
        self.startItem = None
        self.endItem   = None

    def __unicode__(self):
        return u"%s - %s" % (self.startItem, self.endItem)

    def canConnect(self, endItem):
        """
        Test if startitem and specified endslot are compatible
        @rtype boolean
        """
        return self.startItem.interface.canConnectTo(endItem.interface)

    def disconnect(self):
        self.startItem.disconnect(self)
        if self.endItem is not None:
            self.endItem.disconnect(self)

    def moveOrigin(self, pos):
        endpos = self.line().p2()
        #print "Move line", self, pos, endpos
        self.setLine(QLineF(pos, endpos))
        
    def moveEnd(self, pos):
        oripos = self.line().p1()
        #print "Move line", self, oripos, pos
        self.setLine(QLineF(oripos, pos))

    def updatePosition(self):
        offset = QPointF(SlotItem.SIZE/2, SlotItem.SIZE/2, )
        oripos = QPointF()
        if self.startItem is not None:
            orirec = self.startItem.sceneBoundingRect()
            oripos = offset + QPointF(orirec.x(), orirec.y())
            self.moveOrigin(oripos)
        if self.endItem is not None:
            endrec = self.endItem.sceneBoundingRect()
            endpos = offset + QPointF(endrec.x(), endrec.y())
            self.moveEnd(endpos)
        else:
            self.moveEnd(oripos)
    
    def hoverEnterEvent(self, event):
        QObject.emit(self.scene(), SIGNAL("connectorEnterEvent"), self)
        QGraphicsLineItem.hoverEnterEvent(self, event)
    
    def hoverLeaveEvent(self, event):
        QObject.emit(self.scene(), SIGNAL("connectorLeaveEvent"), self)
        QGraphicsLineItem.hoverLeaveEvent(self, event)




class DiagramItem(QGraphicsItemGroup):
    """
    A {DiagramItem} is the graphical representation of a {flow.Node}.
    """
    SVG_SHAPE = ''
    
    def __init__(self, *args):
        QGraphicsItemGroup.__init__(self, *args)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.text = None
        # Underlying object
        self._node = None
        self.buildItem()
        self.slotitems = []

    def __unicode__(self):
        return u"%s" % self.text.toPlainText()

    @property
    def node(self):
        return self._node
    @node.setter
    def node(self, node):
        self._node = node
        self.addSlots()
        self.showSlots()

    @staticmethod
    def factory(classobj):
        mappings = {ProcessNode  : DiagramItemProcess(),
                    InputNode    : DiagramItemInput(),
                    OutputNode   : DiagramItemOutput()}
        for mainclass, diagramitem in mappings.items():
            if issubclass(classobj, mainclass):
                return diagramitem
        raise Exception(_("Unknown node type '%s'") % classobj.__name__)
        
    def buildItem(self):
        self.text = QGraphicsTextItem()
        f = QFont()
        f.setBold(True)
        self.text.setFont(f)
        self.text.setZValue(1000)
        self.addToGroup(self.text)

    def SVGShape(self):
        path = os.path.join(florun.icons_dir, self.SVG_SHAPE)
        if not os.path.exists(path):
            loggui.warning("SVG missing '%s'" % path)
        return path

    def update(self):
        # Update id
        if self.node is not None:
            self.text.setPlainText(self.node.id)
        # Center text item
        itemrect = self.boundingRect()
        textrect = self.text.boundingRect()
        self.text.setPos(QPointF(itemrect.x() + itemrect.width()/2 - textrect.width()/2, 
                                -textrect.height() + itemrect.y() + itemrect.height() / 2))
        if textrect.width() > itemrect.width():
            self.text.setTextWidth(itemrect.width())

    def itemChange(self, change, value):
        # Selection state
        if change == QGraphicsItem.ItemSelectedChange:
            QObject.emit(self.scene(), SIGNAL("selectedChanged"), self)
        # Position
        if change == QGraphicsItem.ItemPositionChange:
            for s in self.slotitems:
                for c in s.connectors:
                    c.updatePosition()
        return QGraphicsItemGroup.itemChange(self, change, value)

    def findSlot(self, interface):
        """
        Find the {SlotItem} matching the specified {flow.Interface}.
        @type interface: {flow.Interface}
        @rtype: {SlotItem}
        """
        for s in self.slotitems:
            if s.interface == interface:
                return s
        raise Exception(u"SlotItem with interface %s not found on %s" % (interface, self))

    def moveEvent(self, event):
        """
        Highlight slots on mouse hover
        """
        for s in self.slotitems:
            #slot_pos = self.mapToItem(s, event.pos())
            rect = s.sceneBoundingRect()
            if rect.contains(event.scenePos()):
                if not s.highlight:
                    QObject.emit(self.scene(), SIGNAL("slotEnterEvent"), s)
                s.highlight = True
            else:
                if s.highlight:
                    QObject.emit(self.scene(), SIGNAL("slotLeaveEvent"), s)
                s.highlight = False
        self.update()

    def hoverMoveEvent(self, event):
        self.moveEvent(event)
        QGraphicsItemGroup.hoverMoveEvent(self, event)

    def hoverEnterEvent(self, event):
        #self.showSlots()
        QObject.emit(self.scene(), SIGNAL("itemEnterEvent"), self)
        QGraphicsItemGroup.hoverEnterEvent(self, event)
    
    def hoverLeaveEvent(self, event):
        QObject.emit(self.scene(), SIGNAL("itemLeaveEvent"), self)
        QGraphicsItemGroup.hoverLeaveEvent(self, event)

    def addSlots(self):
        # Add them all
        textpositions = {Interface.PARAMETER : SlotItem.TEXT_RIGHT,
                         Interface.INPUT     : SlotItem.TEXT_BOTTOM,
                         Interface.RESULT    : SlotItem.TEXT_LEFT,
                         Interface.OUTPUT    : SlotItem.TEXT_TOP,}
        for interface in self.node.interfaces:
            textposition = textpositions.get(interface.type, None)
            slot = SlotItem(self, interface, textposition)
            slot.setVisible(False)
            self.slotitems.append(slot)
            self.addToGroup(slot)

    def showSlots(self, state = True):
        # Show/Hide them all
        for slot in self.slotitems:
            if slot.interface.slot and (state or len(slot.connectors) == 0):
                self.showSlot(slot, state)

    def boundingOffsets(self):
        """
        4-tuple : top, right, bottom, left
        """
        return (0,0,0,0)

    def showSlot(self, slot, state):
        """ 
        Show/Hide specific slot
        @type state : bool
        """
        # Save selected state, restore after
        selected = self.isSelected()
        # Show/Hide slot
        slot.setVisible(state)
        
        # Disconnect all connectors
        if not state:
            for c in slot.connectors:
                self.scene().removeConnector(c, True)
        
        # Spread on side
        rect = self.boundingRect()
        
        # List all visible slot on each side
        left   = [s for s in self.slotitems if s.textposition == SlotItem.TEXT_RIGHT  and s.isVisible()]
        right  = [s for s in self.slotitems if s.textposition == SlotItem.TEXT_LEFT   and s.isVisible()]
        top    = [s for s in self.slotitems if s.textposition == SlotItem.TEXT_BOTTOM and s.isVisible()]
        bottom = [s for s in self.slotitems if s.textposition == SlotItem.TEXT_TOP    and s.isVisible()]
        
        # Find out positions intervals and offsets
        offtop, offright, offbottom, offleft = self.boundingOffsets()
        # slot's textposition allows to know on which side slot appears
        # sidelist    : which list of slots to be handled
        # corner      : which point of reference to spread along side
        # sizex,sizey : which size of refence to spread along side
        if slot.textposition == SlotItem.TEXT_RIGHT:
            sidelist = left
            corner = QPointF(rect.x() + offleft, rect.y())
            sizex, sizey = (0, rect.height())
        elif slot.textposition == SlotItem.TEXT_LEFT:
            sidelist = right
            corner = QPointF(rect.x() + rect.width() + offright, rect.y()) 
            sizex, sizey = (0, rect.height())
        elif slot.textposition == SlotItem.TEXT_BOTTOM:
            sidelist = top
            corner = QPointF(rect.x(), rect.y() + offtop)
            sizex, sizey = (rect.width(), 0)
        elif slot.textposition == SlotItem.TEXT_TOP:
            sidelist = bottom
            corner = QPointF(rect.x(), rect.y() + rect.height() + offbottom)
            sizex, sizey = (rect.width(), 0)
        
        intervalx = sizex / (len(sidelist) + 1)
        intervaly = sizey / (len(sidelist) + 1)
        offset = QPointF(-SlotItem.SIZE/2, -SlotItem.SIZE/2)
        
        for j, s in enumerate(sidelist):
            position = corner + offset + QPointF(intervalx * (j+1), intervaly * (j+1))
            s.setPos(position)
        # Reset selected state that was lost
        self.setSelected(selected)



class DiagramItemProcess(DiagramItem):
    SVG_SHAPE = "item-process.svg"
    def __init__(self, *args):
        DiagramItem.__init__(self, *args)
    
    def buildItem(self):
        DiagramItem.buildItem(self)
        frame = QGraphicsSvgItem(self.SVGShape())
        self.addToGroup(frame)
        self.update()


class DiagramItemInput(DiagramItem):
    SVG_SHAPE = "item-input.svg"

    def buildItem(self):
        DiagramItem.buildItem(self)
        frame = QGraphicsSvgItem(self.SVGShape())
        self.addToGroup(frame)
        self.update()

    def boundingOffsets(self):
        return (0,-10,0,10)

class DiagramItemOutput(DiagramItem):
    SVG_SHAPE = "item-output.svg"

    def buildItem(self):
        DiagramItem.buildItem(self)
        frame = QGraphicsSvgItem(self.SVGShape())
        self.addToGroup(frame)
        self.update()

    def boundingOffsets(self):
        return (0,-10,0,10)

"""

   Diagram scene

"""

class DiagramScene(QGraphicsScene):
    """
    The {DiagramScene} contains all methods to add and remove graphical items.
    Events of user actions are emitted here.
    """
    def __init__(self, *args):
        QGraphicsScene.__init__(self, *args)
        QObject.connect(self, SIGNAL("slotEnterEvent"), self.slotEnterEvent)
        QObject.connect(self, SIGNAL("slotLeaveEvent"), self.slotLeaveEvent)
        QObject.connect(self, SIGNAL("connectorEnterEvent"), self.connectorEnterEvent)
        QObject.connect(self, SIGNAL("connectorLeaveEvent"), self.connectorLeaveEvent)
        QObject.connect(self, SIGNAL("selectedChanged"), self.itemSelected)
        self.connector = None
        self.slot = None
        self.connectorHover = None

    @property
    def window(self):
        return self.parent()

    @property
    def view(self):
        v = self.views()
        if len(v) > 0:
            return v[0]
        return None
    
    def dragEnterEvent(self, event):
        QGraphicsScene.dragEnterEvent(self, event)
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        QGraphicsScene.dragMoveEvent(self, event)
        event.accept()

    def dropEvent(self, event):
        # Create graphical item from string (classname)
        classname = str(event.mimeData().text())
        classobj = eval(classname)
        node = classobj(flow=self.parent().flow)
        self.addDiagramItem(event.scenePos(), node)

    def slotEnterEvent(self, slot):
        self.view.setCursor(Qt.CrossCursor)
        self.slot = slot

    def slotLeaveEvent(self, slot):
        self.view.setCursor(Qt.ArrowCursor)
        self.slot = None

    def connectorEnterEvent(self, connector):
        self.view.setCursor(Qt.CrossCursor)
        self.connectorHover = connector

    def connectorLeaveEvent(self, connector):
        self.view.setCursor(Qt.ArrowCursor)
        self.connectorHover = None

    def addDiagramItem(self, pos, node, emit=True):
        item = DiagramItem.factory(node.__class__)
        item.node = node
        item.setPos(pos)
        self.addItem(item)
        item.update()
        if emit:
            QObject.emit(self.window, SIGNAL("diagramItemCreated"), item)
        return item
        
    def removeDiagramItem(self, item):
        for slot in item.slotitems:
            for connector in slot.connectors:
                self.removeConnector(connector)
        self.removeItem(item)
        QObject.emit(self.window, SIGNAL("diagramItemRemoved"), item)

    def addConnector(self, startSlot, endSlot=None, emit=True):
        connector = DiagramConnector()
        self.addItem(connector)
        startSlot.connect(connector)
        # If endSlot is not given, then the user is now drawing 
        if endSlot is not None:
            endSlot.connect(connector, False)
            loggui.debug("%s %s" % (self.tr(u"Connector added"), connector))
            if emit:
                QObject.emit(self.window, SIGNAL("connectorCreated"), connector)
        connector.updatePosition()
        return connector

    def removeConnector(self, connector, event=False):
        connector.disconnect()
        self.removeItem(connector)
        self.connectorLeaveEvent(connector)
        if event:
            loggui.debug("%s %s" % (self.tr(u"Connector removed"), connector))
            QObject.emit(self.window, SIGNAL("connectorRemoved"), connector)

    def findDiagramItemByNode(self, node):
        for i in self.items():
            if issubclass(i.__class__, DiagramItem):
                if i.node == node:
                    return i
        raise Exception("%s : %s" % (self.tr(u"DiagramItem not found with node"), node))

    def mousePressEvent(self, mouseEvent):
        if self.slot is not None:
            self.connector = self.addConnector(self.slot)
        QGraphicsScene.mousePressEvent(self, mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        pos = mouseEvent.scenePos()
        # If connector is not None, the user is drawing
        if self.connector is not None:
            self.connector.moveEnd(pos)
        # Gives sub items mouse move if mouse pressed
        if mouseEvent.buttons() != Qt.NoButton :
            for i in self.items(pos):
                if issubclass(i.__class__, DiagramItem):
                    i.moveEvent(mouseEvent)
        if self.connector is None:
            QGraphicsScene.mouseMoveEvent(self, mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        if self.connectorHover is not None:
            # Connector was clicked : remove it
            self.removeConnector(self.connectorHover, True)
        elif self.connector is not None:
            # Create connector
            if self.slot is not None:
                if self.connector.canConnect(self.slot):
                    # New connector, remove the one being drawn
                    self.removeConnector(self.connector)
                    # Add the new one with both ends
                    self.addConnector(self.connector.startItem, self.slot)
                else:
                    # For some reason, start and end slots could not be connected.
                    self.window.setStatusMessage(self.tr("Incompatible slots"))
                    self.removeConnector(self.connector)
            else:
                # Mouse was released outside slot
                self.removeConnector(self.connector)
        self.connector = None
        self.slot = None
        QGraphicsScene.mouseReleaseEvent(self, mouseEvent)
    
    def itemSelected(self, item):
        if issubclass(item.__class__, DiagramItem):
            QObject.emit(self.window, SIGNAL("selectedChanged"), item)


"""

   Library of Nodes

"""

class NodeLibrary(QToolBox):
    """
    The {NodeLibrary} contains different sets of {LibraryItem}s.
    The {QtGui.QToolBox} allows to have collapsable widgets.
    """
    MAX_PER_LINE = 2
    def __init__(self, *args):
        QToolBox.__init__(self, *args)
        self.loadSets()

    def loadSets(self):
        libs = groupby([c for c in itersubclasses(Node) if c.label != ''], 'category')
        # Add sets according to groups
        for itemgroup in libs:
            set = []
            for classobj in sorted(itemgroup, cmp=lambda x,y: cmp(x.label, y.label)):
                item = DiagramItem.factory(classobj)
                loggui.debug(u"Adding %s/%s in nodes library" % (type(item).__name__, classobj.__name__))
                item = LibraryItem(classobj.__name__, classobj.label, item.SVGShape())
                set.append(item)
            self.addSet(set, itemgroup[0].category)

    def addSet(self, widgets, label):
        """
        @type widgets : list of {LibraryItem}
        @param label  : the name of the set of items
        @type label   : string
        
        """
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        for i, widget in enumerate(widgets):
            layout.addWidget(widget, int(i / self.MAX_PER_LINE), i % self.MAX_PER_LINE)
        list = QWidget()
        list.setLayout(layout)
        self.addItem(list, label)


class LibraryItem(QFrame):
    def __init__(self, id, label, iconfile):
        QFrame.__init__(self)
        self.id = id
        # An Icon and a label below
        icon = QLabel()
        icon.setPixmap(QPixmap(iconfile).scaledToWidth(50))
        layout = QGridLayout()
        layout.addWidget(icon, 0, 0, Qt.AlignHCenter)
        title = QLabel(label)
        font = title.font()
        font.setPixelSize(10)
        title.setFont(font)
        layout.addWidget(title, 1, 0, Qt.AlignTop|Qt.AlignHCenter)
        self.setLayout(layout)
        self.setMaximumSize(80, 80)
    
    @property
    def window(self):
        #TODO: what better way ?
        return self.parent().parent().parent().parent().parent().parent().parent().parent()

    """
    Drag and drop management
    """
    def enterEvent(self, event):
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setCursor(Qt.OpenHandCursor)
        # Show description in status bar
        self.window.setStatusMessage(eval(self.id).description)
        
    def leaveEvent(self, event):
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, mouseEvent):
        self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, mouseEvent):
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        # Drag-n-Drop on left clic :
        if event.buttons() != Qt.LeftButton:
            return
        # Store the classname of the node in the D-n-D
        mimeData = QMimeData()
        mimeData.setText(self.id)
        # Initialize Drag-and-drop action
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setHotSpot(event.pos() - self.rect().topLeft())

        dropAction = drag.start(Qt.MoveAction)
        if dropAction == Qt.MoveAction:
            self.close()


"""

    Parameters Editor

"""
class ParameterField(QWidget):
    def __init__(self, interface, *args):
        QWidget.__init__(self, *args)
        self.interface = interface
        
        self.label = self.tr(interface.name)
        value = ''
        if interface.value is not None:
            value = interface.value
        
        self.edit     = QLineEdit(value, self)
        self.checkbox = QCheckBox(self.tr(u'slot'), self)
        self.checkbox.setToolTip(self.tr(u'Use slot input'))
        
        layout = QHBoxLayout()
        #layout.addWidget(QLabel(self.label))
        layout.addWidget(self.edit)
        layout.addWidget(self.checkbox)
        self.setLayout(layout)
        self.setToolTip(interface.doc)
        self.update()

    def update(self):
        self.checkbox.setCheckState(Qt.Checked if self.interface.slot else Qt.Unchecked)
        self.edit.setEnabled(not self.interface.slot)
        if self.interface.slot: self.edit.setText('')


class ParametersEditor(QGroupBox):
    def __init__(self, parent, scene, *args):
        QGroupBox.__init__(self, *args)
        self.parent = parent
        self.scene = scene
        
        # Actions
        self.btnDelete = QPushButton(self.tr("Delete"))
        self.btnDelete.setIcon(self.parent.loadIcon(QStyle.SP_TrashIcon)) 
        self.btnCancel = QPushButton(self.tr("Undo"))
        self.btnCancel.setIcon(self.parent.loadIcon(QStyle.SP_DialogCancelButton))
        self.btnSave = QPushButton(self.tr("Apply"))
        self.btnSave.setIcon(self.parent.loadIcon(QStyle.SP_DialogOkButton))
        
        # Buttons
        buttonslayout = QHBoxLayout()
        buttonslayout.addWidget(self.btnDelete)
        buttonslayout.addWidget(self.btnCancel)
        buttonslayout.addWidget(self.btnSave)
        
        # Main Layout
        self.mainlayout = QVBoxLayout()
        self.mainlayout.addStretch()
        
        buttonswidget = QWidget()
        buttonswidget.setLayout(buttonslayout)
        self.mainlayout.addWidget(buttonswidget)
        
        self.setTitle(self.tr("Parameters"))
        self.setLayout(self.mainlayout)
        # Actions
        QObject.connect(self.btnDelete, SIGNAL("clicked()"), self.delete)
        QObject.connect(self.btnCancel, SIGNAL("clicked()"), self.cancel)
        QObject.connect(self.btnSave,   SIGNAL("clicked()"), self.save)
        
        # Form item
        self.formwidget = None
        self.formlayout = None
        self.item       = None
        self.nodeId     = None
        self.extrafields = {}
        
        # Init form with default fields
        self.clear()

    def enable(self):
        state = self.item is not None
        self.nodeId.setEnabled(state)
        #TODO: enable extra widgets
        self.btnDelete.setEnabled(state)
        self.btnCancel.setEnabled(state)
        self.btnSave.setEnabled(state)
    
    def clear(self):
        if self.formwidget is not None:
            self.mainlayout.removeWidget(self.formwidget)
            self.formwidget.setParent(None)
        
        # Common fields
        self.nodeId = QLineEdit('', self)
        self.formlayout = QFormLayout()
        self.formlayout.addRow(self.tr("Id"), self.nodeId)
        
        self.formwidget = QWidget()
        self.formwidget.setLayout(self.formlayout)
        self.mainlayout.insertWidget(0, self.formwidget)
        
        self.item = None
        self.extrafields = {}
        
        # Enable widgets
        self.enable()

    def delete(self):
        self.scene.removeDiagramItem(self.item)
        self.clear()
        
    def cancel(self):
        self.load(self.item)

    def load(self, item):
        self.clear()
        self.item = item
        self.nodeId.setText(item.node.id)
        # For each node interface, add a widget
        for interface in item.node.interfaces:
            if interface.isValue() and interface.isInput():
                w = ParameterField(interface)
                # Trick to have tooltip on form row
                qlabel = QLabel(w.label)
                qlabel.setToolTip(w.interface.doc)
                self.formlayout.addRow(qlabel, w)
                # Connect checkbox event
                QObject.connect(w.checkbox, SIGNAL("stateChanged(int)"), self.showSlot)
                # Keep track of associations for saving
                self.extrafields[interface.name] = w
        self.enable()
    
    def save(self):
        self.item.node.id = self.nodeId.text()
        # Save Interface values (from GUI to flow)
        for interface in self.item.node.interfaces:
            w = self.extrafields.get(interface.name, None)
            if w is not None:
                interface.value = w.edit.text()
            else:
                loggui.warning("Why cannot find '%s' among fields ?" % interface.name)
        self.item.update()
    
    def showSlot(self, state):
        for w in self.extrafields.values():
            checked = w.checkbox.checkState() == Qt.Checked
            # State changed ?
            if w.interface.slot != checked:
                w.interface.slot = checked
                w.update() # Enable/disable widget
                # Show/Hide slot on item
                slot = self.item.findSlot(w.interface)
                self.item.showSlot(slot, checked)
                

class FlowConsole(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        self.process = None
        
        self.cbloglevel = QComboBox()
        self.cbloglevel.insertItem(0, self.tr("Errors only"), logcore.ERROR)
        self.cbloglevel.insertItem(1, self.tr("Warnings"),    logcore.WARNING)
        self.cbloglevel.insertItem(2, self.tr("Information"), logcore.INFO)
        self.cbloglevel.insertItem(3, self.tr("Debug messages"), logcore.DEBUG)
        self.cbloglevel.setCurrentIndex(2)
        
        self.lblloglevel = QLabel(self.tr("Output"))
        self.lblloglevel.setBuddy(self.cbloglevel)
        
        hlbox = QHBoxLayout()
        hlbox.addWidget(self.lblloglevel)
        hlbox.addWidget(self.cbloglevel)
        hlbox.addStretch()
        hbox = QWidget()
        hbox.setLayout(hlbox)
        
        self.console = QTextEdit()
        
        self.mainlayout = QVBoxLayout()
        self.mainlayout.addWidget(hbox)
        self.mainlayout.addWidget(self.console)    
        self.setLayout(self.mainlayout)
    
    @property
    def loglevel(self):
        idx = self.cbloglevel.currentIndex()
        integer, canconvert = self.cbloglevel.itemData(idx).toInt()
        return integer        

    def enable(self):
        self.cbloglevel.setEnabled(self.process is None)
        
    def attachProcess(self, process):
        self.process = process
        self.console.clear()
        self.enable()
    
    def detachProcess(self):
        self.process = None
        self.enable()
        
    def updateConsole(self):
        if self.process is not None:
            stdout = QString(self.process.readAllStandardOutput()).trimmed()
            if stdout != "":
                self.console.append("<span style=\"color: black\">" + stdout.replace("\n", "<br/>") + "</span>")
            stderr = QString(self.process.readAllStandardError()).trimmed()
            if stderr != "":
                self.console.append("<span style=\"color: red\">" + stderr.replace("\n", "<br/>") + "</span>")
            

"""

    Main Window

"""

class MainWindow(QMainWindow):
    def __init__(self, filename=None, *args):
        QMainWindow.__init__(self, *args)
        self.apptitle = florun.__title__
        # Main attributes 
        self.basedir = florun.base_dir
        self.flow = None
        self.buildActions()
        self.buildWidgets()
        # Center of the screen
        self.center()
        # Init
        if filename is not None:
            self.loadFlow(filename)
        else:
            self.newFlow()
        self.updateTitle()

    def buildWidgets(self):
        # Main widgets
        self.statusBar()
        self.buildMenuToolbar()
        """
        Diagram Panel
        """
        # Scene
        self.scene = DiagramScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        # Node library
        self.nodelibrary = NodeLibrary()
        # Parameters Panel
        self.parameters = ParametersEditor(self, self.scene)
        # Put it all together
        diagrampanel = QSplitter()
        diagrampanel.addWidget(self.nodelibrary)
        diagrampanel.addWidget(self.view)
        diagrampanel.addWidget(self.parameters)
        diagrampanel.setSizes([180, 400, 150])
        diagrampanel.setStretchFactor(0, 0)
        diagrampanel.setStretchFactor(1, 1)
        diagrampanel.setStretchFactor(2, 0)
        
        """
        Console Panel
        """
        self.console = FlowConsole(self)
        
        # Build tabs
        self.maintabs = QTabWidget()
        self.maintabs.addTab(diagrampanel, self.tr("Scheme"))
        self.maintabs.addTab(self.console, self.tr("Console"))    
        self.setCentralWidget(self.maintabs)
        
        # Connect events
        QObject.connect(self, SIGNAL("selectedChanged"),    self.diagramItemSelected)
        QObject.connect(self, SIGNAL("diagramItemCreated"), self.diagramItemCreated)
        QObject.connect(self, SIGNAL("diagramItemRemoved"), self.diagramItemRemoved)
        QObject.connect(self, SIGNAL("connectorCreated"), self.connectorCreated)
        QObject.connect(self, SIGNAL("connectorRemoved"), self.connectorRemoved)

    def updateTitle(self):
        filename = self.flow.filename
        if filename is None:
            filename = self.tr(u"Untitled")
        if self.flow.modified:
            filename = "*"+filename
        self.setWindowTitle("%s - %s" % (filename, self.apptitle))

    def setStatusMessage(self, txt, timeout=3000):
        self.statusBar().showMessage(txt, timeout)

    def loadIcon(self, iconid):
        """
        @param iconid : Freedesktop identifier from http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
        @type iconid : str
        @rtype: L{QtGui.QIcon}
        """
        #style = self.style()
        #return style.standardIcon(pixmap)
        try:
            if QIcon.hasThemeIcon(iconid):
                return QIcon.fromTheme(iconid)
        except AttributeError, e:
            pass
        # Guess path of icon
        base = '/usr/share/icons/'
        find = QProcess()
        find.start('find %s -name "%s*"' % (base, iconid))
        if find.waitForFinished():
            list = QString(find.readAllStandardOutput()).split("\n")
            if len(list) > 0:
                path = list[0]
                loggui.debug("Load icon file from '%s'" % path)
                return QIcon(QPixmap(path))
        raise Exception("Could not find icon '%s'" % iconid)

    def buildActions(self):
        self.new = QAction(self.loadIcon('document-new'), self.tr('New'), self)
        self.new.setShortcut('Ctrl+N')
        self.new.setStatusTip(self.tr('New flow'))
        self.connect(self.new, SIGNAL('triggered()'), self.newFlow)
        
        self.open = QAction(self.loadIcon('document-open'), self.tr('Open'), self)
        self.open.setShortcut('Ctrl+O')
        self.open.setStatusTip(self.tr('Open flow'))
        self.connect(self.open, SIGNAL('triggered()'), self.loadFlow)

        self.save = QAction(self.loadIcon('document-save'), self.tr('Save'), self)
        self.save.setShortcut('Ctrl+S')
        self.save.setStatusTip(self.tr('Save flow'))
        self.connect(self.save, SIGNAL('triggered()'), self.saveFlow)
         
        self.exit = QAction(self.loadIcon('application-exit'), self.tr('Exit'), self)
        self.exit.setShortcut('Ctrl+Q')
        self.exit.setStatusTip(self.tr('Exit application'))
        self.connect(self.exit, SIGNAL('triggered()'), SLOT('close()'))
        
        self.start = QAction(self.loadIcon('media-playback-start'), self.tr('Start'), self)
        self.start.setShortcut('Ctrl+R')
        self.start.setStatusTip(self.tr('Start flow'))
        self.connect(self.start, SIGNAL('triggered()'), self.startFlow)
        
        self.stop = QAction(self.loadIcon('media-playback-stop'), self.tr('Stop'), self)
        self.stop.setShortcut('Ctrl+S')
        self.stop.setStatusTip(self.tr('Stop running flow'))
        self.connect(self.stop, SIGNAL('triggered()'), self.stopFlow)
        self.stop.setEnabled(False)
    
    def updateSavedState(self):
        self.updateTitle()
        self.save.setEnabled(self.flow.modified)
    
    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
    def buildMenuToolbar(self):
        menubar = self.menuBar()
        file = menubar.addMenu(self.tr('&Flow'))
        file.addAction(self.new)
        file.addAction(self.open)
        file.addAction(self.save)
        file.addAction(self.exit)

        toolbar = self.addToolBar(self.tr('Main'))
        toolbar.addAction(self.new)
        toolbar.addAction(self.open)
        toolbar.addAction(self.save)
        
        toolbar.addSeparator()
        toolbar.addAction(self.start)
        toolbar.addAction(self.stop)
        
        toolbar.addSeparator()
        toolbar.addAction(self.exit)

    @classmethod
    def messageException(cls, excType, excValue, tracebackobj):
        errmsg = u"%s: %s" % (str(excType), str(excValue))
        tbinfofile = cStringIO.StringIO()
        traceback.print_tb(tracebackobj, None, tbinfofile)
        tbinfofile.seek(0)
        tbinfo = tbinfofile.read()
        
        logcore.debug(errmsg + "\n" + tbinfo)

        errorbox = QMessageBox()
        errorbox.setIcon(QMessageBox.Critical)
        errorbox.setText(u"An unhandled exception occurred.")
        errorbox.setInformativeText(errmsg)
        errorbox.setDetailedText(tbinfo)
        errorbox.exec_()

    @classmethod
    def messageCancelYesNo(cls, mainText, infoText):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText(mainText)
        msgBox.setInformativeText(infoText)
        msgBox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Save)
        return msgBox.exec_()

    """
    
    Scene events
    
    """
    
    def diagramItemSelected(self, item):
        if not item.isSelected():
            self.parameters.load(item)
        else:
            self.parameters.clear()
    
    def diagramItemCreated(self, item):
        loggui.debug("%s : %s" % (self.tr("Main window: diagram item created"),item))
        self.flow.addNode(item.node)
        self.updateSavedState()

    def diagramItemRemoved(self, item):
        loggui.debug("%s : %s" % (self.tr("Main window: diagram item removed"),item))
        self.flow.removeNode(item.node)
        self.updateSavedState()
        
    def connectorCreated(self, connector):
        loggui.debug("%s : %s" % (self.tr("Main window: diagram connector created"),connector))
        start = connector.startItem.interface
        end = connector.endItem.interface
        self.flow.addConnector(start, end)
        self.updateSavedState()
    
    def connectorRemoved(self, connector):
        loggui.debug("%s : %s" % (self.tr("Main window: diagram connector removed"),connector))
        start = connector.startItem.interface
        end = connector.endItem.interface
        self.flow.removeConnector(start, end)
        self.updateSavedState()


    """
    
    Main events
    
    """
    
    def closeEvent(self, event):
        """
        Close the window.
        """
        # Ask to save if flow was modified
        if self.flow.modified:
            answer = self.messageCancelYesNo(self.tr(u"The flow has been modified."),
                                             self.tr("Do you want to save your changes?"))
            if answer == QMessageBox.Save:
                if not self.saveFlow():
                    event.ignore() # Was not saved, don't close
                    return
            if answer == QMessageBox.Cancel:
                event.ignore() # Don't close
                return
        event.accept()

    def newFlow(self):
        """
        Start a new flow
        """
        # Ask to save if flow was modified
        if self.flow is not None:
            if self.flow.modified:
                answer = self.messageCancelYesNo(self.tr(u"The flow has been modified."),
                                                 self.tr("Do you want to save your changes?"))
                if answer == QMessageBox.Save:
                    if not self.saveFlow():
                        return # Was not saved, don't clear.
                if answer == QMessageBox.Cancel:
                    return # Don't clear
        self.flow = Flow()
        self.scene.clear()
        self.parameters.clear()
        self.updateSavedState()

    def loadFlow(self, filename=None):
        """
        Load a flow from a file.
        """
        if filename is None:
            # Ask the user
            filename = unicode(QFileDialog.getOpenFileName(self, self.tr('Open file'), self.basedir))
            if filename == '': # User clicked cancel
                return

        loggui.debug(u"Load file '%s'..." % filename)
        self.basedir = os.path.dirname(filename)
        self.flow = Flow.load(filename)
        self.scene.clear()
        self.parameters.clear()
        # Add graphical items
        for i, n in enumerate(self.flow.nodes):
            posx = n.graphicalprops.get('x', 50 * i)
            posy = n.graphicalprops.get('y', 50 * i)
            pos = QPointF(posx, posy)
            diagramitem = self.scene.addDiagramItem(pos=pos, node=n, emit=False)
        # Add connectors
        for n in self.flow.nodes:
            for interface in n.interfaces:
                startitem = self.scene.findDiagramItemByNode(n)
                startslot = startitem.findSlot(interface)
                for successor in interface.successors:
                    enditem = self.scene.findDiagramItemByNode(successor.node)
                    endslot = enditem.findSlot(successor)
                    self.scene.addConnector(startslot, endslot, emit=False)
        self.updateSavedState()
    
    def saveFlow(self):
        """
        Save a flow to a file
        """
        # Ask the user if never saved
        if self.flow.filename is None:
            ask = QFileDialog.getSaveFileName(self, self.tr('Save file'), self.basedir)
            ask = unicode(ask) # convert QString
            if ask == '': # User clicked cancel
                return False
            self.flow.filename = ask
        # Set graphical properties (positions, etc)
        for item in self.scene.items():
            if issubclass(item.__class__, DiagramItem):
                pos = item.scenePos()
                item.node.graphicalprops['x'] = pos.x()
                item.node.graphicalprops['y'] = pos.y()
        loggui.debug(u"Save file '%s'..." % self.flow.filename)
        self.flow.save()
        self.updateSavedState()
        return True
    
    def startFlow(self):
        """
        Run current flow
        """
        # Switch to console tab
        self.maintabs.setCurrentIndex(1)
        # Disable start
        self.start.setEnabled(False)
        self.stop.setEnabled(True)
        # Use process
        self.process = QProcess()
        self.console.attachProcess(self.process)
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"), self.console.updateConsole)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),  self.console.updateConsole)
        # Run command
        florunmain = os.path.join(florun.base_dir, 'florun.py')
        cmd = 'python %s --level %s --execute "%s"' % (florunmain, self.console.loglevel, self.flow.filename)
        loggui.debug(self.tr("Start command '%s'" % cmd))
        self.process.start(cmd)
        # Now wait...
        if not self.process.waitForStarted():
            self.process.kill()
            raise Exception(self.tr("Could not execute flow : %s" % self.process.error())) 
        self.process.waitForFinished()
        self.console.detachProcess()
        self.start.setEnabled(True)
        self.stop.setEnabled(False)

    def stopFlow(self):
        """
        Stop current flow
        """
        # Interrupt running thread
        self.process.kill()
        self.console.detachProcess()
        self.process = None
        self.start.setEnabled(True)
        self.stop.setEnabled(False)


def main(args, filename=None):
    app = QApplication(args)
    mainWindow = MainWindow(filename)
    mainWindow.setGeometry(100, 100, 800, 500)
    mainWindow.show()
    # Replace system exception hook with GUI
    sys.excepthook = mainWindow.messageException
    # Qt Main loop
    return app.exec_()

if __name__ == "__main__":
    main(sys.argv)