# -*- coding: utf-8 -*-
"""
widgets.py -  Interactive graphics items for GraphicsView (ROI widgets)
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.

Implements a series of graphics items which display movable/scalable/rotatable shapes
for use as region-of-interest markers. ROI class automatically handles extraction 
of array data from ImageItems.
"""

from PyQt4 import QtCore, QtGui, QtOpenGL, QtSvg
from numpy import array, arccos, dot, pi, zeros, vstack, ubyte, fromfunction, ceil, floor
from numpy.linalg import norm
import scipy.ndimage as ndimage
from Point import *
from math import cos, sin

def rectStr(r):
    return "[%f, %f] + [%f, %f]" % (r.x(), r.y(), r.width(), r.height())

## Multiple inheritance not allowed in PyQt. Retarded workaround:
class QObjectWorkaround:
    def __init__(self):
        self._qObj_ = QtCore.QObject()
    def __getattr__(self, attr):
        if attr == '_qObj_':
            raise Exception("QObjectWorkaround not initialized!")
        return getattr(self._qObj_, attr)
    def connect(self, *args):
        return QtCore.QObject.connect(self._qObj_, *args)


class ROI(QtGui.QGraphicsItem, QObjectWorkaround):
    def __init__(self, pos, size=Point(1, 1), angle=0.0, invertible=False, maxBounds=None, snapSize=1.0, scaleSnap=False, translateSnap=False, rotateSnap=False, parent=None):
        QObjectWorkaround.__init__(self)
        QtGui.QGraphicsItem.__init__(self, parent)
        pos = Point(pos)
        size = Point(size)
        self.aspectLocked = False
        self.translatable = True
        
        self.pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        self.handlePen = QtGui.QPen(QtGui.QColor(150, 255, 255))
        self.handles = []
        self.state = {'pos': pos, 'size': size, 'angle': angle}
        self.lastState = None
        self.setPos(pos)
        self.rotate(-angle)
        self.setZValue(10)
        
        self.handleSize = 4
        self.invertible = invertible
        self.maxBounds = maxBounds
        
        self.snapSize = snapSize
        self.translateSnap = translateSnap
        self.rotateSnap = rotateSnap
        self.scaleSnap = scaleSnap
        self.setFlag(self.ItemIsSelectable, True)
        
    def setZValue(self, z):
        QtGui.QGraphicsItem.setZValue(self, z)
        for h in self.handles:
            h['item'].setZValue(z+1)
        
    def sceneBounds(self):
        return self.sceneTransform().mapRect(self.boundingRect())
    
    def parentBounds(self):
        return self.mapToParent(self.boundingRect()).boundingRect()

    def setPen(self, pen):
        self.pen = pen
        self.update()
        
    def setPos(self, pos, update=True):
        pos = Point(pos)
        self.state['pos'] = pos
        QtGui.QGraphicsItem.setPos(self, pos)
        if update:
            self.handleChange()
        
    def setSize(self, size, update=True):
        size = Point(size)
        self.prepareGeometryChange()
        self.state['size'] = size
        if update:
            self.updateHandles()
            self.handleChange()
        
    def addTranslateHandle(self, pos, axes=None, item=None):
        pos = Point(pos)
        return self.addHandle({'type': 't', 'pos': pos, 'item': item})
    
    def addScaleHandle(self, pos, center, axes=None, item=None):
        pos = Point(pos)
        center = Point(center)
        info = {'type': 's', 'center': center, 'pos': pos, 'item': item}
        if pos.x() == center.x():
            info['xoff'] = True
        if pos.y() == center.y():
            info['yoff'] = True
        return self.addHandle(info)
    
    def addRotateHandle(self, pos, center, item=None):
        pos = Point(pos)
        center = Point(center)
        return self.addHandle({'type': 'r', 'center': center, 'pos': pos, 'item': item})
    
    def addScaleRotateHandle(self, pos, center, item=None):
        pos = Point(pos)
        center = Point(center)
        if pos[0] != center[0] and pos[1] != center[1]:
            raise Exception("Scale/rotate handles must have either the same x or y coordinate as their center point.")
        return self.addHandle({'type': 'sr', 'center': center, 'pos': pos, 'item': item})
    
    def addHandle(self, info):
        if not info.has_key('item') or info['item'] is None:
            #print "BEFORE ADD CHILD:", self.childItems()
            h = Handle(self.handleSize, typ=info['type'], pen=self.handlePen, parent=self)
            #print "AFTER ADD CHILD:", self.childItems()
            h.setPos(info['pos'] * self.state['size'])
            info['item'] = h
        else:
            h = info['item']
        iid = len(self.handles)
        h.connectROI(self, iid)
        #h.mouseMoveEvent = lambda ev: self.pointMoveEvent(iid, ev)
        #h.mousePressEvent = lambda ev: self.pointPressEvent(iid, ev)
        #h.mouseReleaseEvent = lambda ev: self.pointReleaseEvent(iid, ev)
        self.handles.append(info)
        h.setZValue(self.zValue()+1)
        #if self.isSelected():
            #h.show()
        #else:
            #h.hide()
        return h
        
    def mapSceneToParent(self, pt):
        return self.mapToParent(self.mapFromScene(pt))

    def setSelected(self, s):
        QtGui.QGraphicsItem.setSelected(self, s)
        #print "select", self, s
        if s:
            for h in self.handles:
                h['item'].show()
        else:
            for h in self.handles:
                h['item'].hide()

    def mousePressEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            self.setSelected(True)
            if self.translatable:
                self.cursorOffset = self.scenePos() - ev.scenePos()
                self.emit(QtCore.SIGNAL('regionChangeStarted'), self)
                ev.accept()
        else:
            ev.ignore()
        
    def mouseMoveEvent(self, ev):
        #print "mouse move", ev.pos()
        if self.translatable:
            snap = None
            if self.translateSnap or (ev.modifiers() & QtCore.Qt.ControlModifier):
                snap = Point(self.snapSize, self.snapSize)
            newPos = ev.scenePos() + self.cursorOffset
            newPos = self.mapSceneToParent(newPos)
            self.translate(newPos - self.pos(), snap=snap)
    
    def mouseReleaseEvent(self, ev):
        if self.translatable:
            self.emit(QtCore.SIGNAL('regionChangeFinished'), self)
    
    
    
    def pointPressEvent(self, pt, ev):
        #print "press"
        self.emit(QtCore.SIGNAL('regionChangeStarted'), self)
        #self.pressPos = self.mapFromScene(ev.scenePos())
        #self.pressHandlePos = self.handles[pt]['item'].pos()
    
    def pointReleaseEvent(self, pt, ev):
        #print "release"
        self.emit(QtCore.SIGNAL('regionChangeFinished'), self)
    
    def stateCopy(self):
        sc = {}
        sc['pos'] = Point(self.state['pos'])
        sc['size'] = Point(self.state['size'])
        sc['angle'] = self.state['angle']
        return sc
    
    def updateHandles(self):
        #print "update", self.handles
        for h in self.handles:
            #print "  try", h
            if h['item'] in self.childItems():
                p = h['pos']
                h['item'].setPos(h['pos'] * self.state['size'])
            #else:
                #print "    Not child!", self.childItems()
        
    
    def checkPointMove(self, pt, pos, modifiers):
        return True
    
    def pointMoveEvent(self, pt, ev):
        self.movePoint(pt, ev.scenePos(), ev.modifiers())
        
        
    def movePoint(self, pt, pos, modifiers=QtCore.Qt.KeyboardModifier()):
        #print "movePoint", pos
        newState = self.stateCopy()
        h = self.handles[pt]
        #p0 = self.mapToScene(h['item'].pos())
        p0 = self.mapToScene(h['pos'] * self.state['size'])
        p1 = Point(pos)
        p0 = self.mapSceneToParent(p0)
        p1 = self.mapSceneToParent(p1)

        if h.has_key('center'):
            c = h['center']
            cs = c * self.state['size']
            #lpOrig = h['pos'] - 
            #lp0 = self.mapFromScene(p0) - cs
            #lp1 = self.mapFromScene(p1) - cs
            lp0 = self.mapFromParent(p0) - cs
            lp1 = self.mapFromParent(p1) - cs
        
        if h['type'] == 't':
            #p0 = Point(self.mapToScene(h['item'].pos()))
            #p1 = Point(pos + self.mapToScene(self.pressHandlePos) - self.mapToScene(self.pressPos))
            snap = None
            if self.translateSnap or (modifiers & QtCore.Qt.ControlModifier):
                snap = Point(self.snapSize, self.snapSize)
            self.translate(p1-p0, snap=snap, update=False)
        
        elif h['type'] == 's':
            #c = h['center']
            #cs = c * self.state['size']
            #p1 = (self.mapFromScene(ev.scenePos()) + self.pressHandlePos - self.pressPos) - cs
            
            if h['center'][0] == h['pos'][0]:
                lp1[0] = 0
            if h['center'][1] == h['pos'][1]:
                lp1[1] = 0
            
            if self.scaleSnap or (modifiers & QtCore.Qt.ControlModifier):
                lp1[0] = round(lp1[0] / self.snapSize) * self.snapSize
                lp1[1] = round(lp1[1] / self.snapSize) * self.snapSize
            
            hs = h['pos'] - c
            if hs[0] == 0:
                hs[0] = 1
            if hs[1] == 0:
                hs[1] = 1
            newSize = lp1 / hs
            
            if newSize[0] == 0:
                newSize[0] = newState['size'][0]
            if newSize[1] == 0:
                newSize[1] = newState['size'][1]
            if not self.invertible:
                if newSize[0] < 0:
                    newSize[0] = newState['size'][0]
                if newSize[1] < 0:
                    newSize[1] = newState['size'][1]
            if self.aspectLocked:
                newSize[0] = newSize[1]
            
            s0 = c * self.state['size']
            s1 = c * newSize
            cc = self.mapToParent(s0 - s1) - self.mapToParent(Point(0, 0))
            
            newState['size'] = newSize
            newState['pos'] = newState['pos'] + cc
            if self.maxBounds is not None:
                r = self.stateRect(newState)
                if not self.maxBounds.contains(r):
                    return
            
            self.setPos(newState['pos'], update=False)
            self.prepareGeometryChange()
            self.state = newState
            
            self.updateHandles()
        
        elif h['type'] == 'r':
            #newState = self.stateCopy()
            #c = h['center']
            #cs = c * self.state['size']
            #p0 = Point(h['item'].pos()) - cs
            #p1 = (self.mapFromScene(ev.scenePos()) + self.pressHandlePos - self.pressPos) - cs
            if lp1.length() == 0 or lp0.length() == 0:
                return
            
            ang = newState['angle'] + lp0.angle(lp1)
            if ang is None:
                return
            if self.rotateSnap or (modifiers & QtCore.Qt.ControlModifier):
                ang = round(ang / (pi/12.)) * (pi/12.)
            
            
            tr = QtGui.QTransform()
            tr.rotate(-ang * 180. / pi)
            
            cc = self.mapToParent(cs) - (tr.map(cs) + self.state['pos'])
            newState['angle'] = ang
            newState['pos'] = newState['pos'] + cc
            if self.maxBounds is not None:
                r = self.stateRect(newState)
                if not self.maxBounds.contains(r):
                    return
            self.setTransform(tr)
            self.setPos(newState['pos'], update=False)
            self.state = newState
        
        elif h['type'] == 'sr':
            #newState = self.stateCopy()
            if h['center'][0] == h['pos'][0]:
                scaleAxis = 1
            else:
                scaleAxis = 0
            
            #c = h['center']
            #cs = c * self.state['size']
            #p0 = Point(h['item'].pos()) - cs
            #p1 = (self.mapFromScene(ev.scenePos()) + self.pressHandlePos - self.pressPos) - cs
            if lp1.length() == 0 or lp0.length() == 0:
                return
            
            ang = newState['angle'] + lp0.angle(lp1)
            if ang is None:
                return
            if self.rotateSnap or (modifiers & QtCore.Qt.ControlModifier):
                ang = round(ang / (pi/12.)) * (pi/12.)
            
            hs = abs(h['pos'][scaleAxis] - c[scaleAxis])
            newState['size'][scaleAxis] = lp1.length() / hs
            if self.scaleSnap or (modifiers & QtCore.Qt.ControlModifier):
                newState['size'][scaleAxis] = round(newState['size'][scaleAxis] / self.snapSize) * self.snapSize
            if newState['size'][scaleAxis] == 0:
                newState['size'][scaleAxis] = 1
                
            c1 = c * newState['size']
            tr = QtGui.QTransform()
            tr.rotate(-ang * 180. / pi)
            
            cc = self.mapToParent(cs) - (tr.map(c1) + self.state['pos'])
            newState['angle'] = ang
            newState['pos'] = newState['pos'] + cc
            if self.maxBounds is not None:
                r = self.stateRect(newState)
                if not self.maxBounds.contains(r):
                    return
            self.setTransform(tr)
            self.setPos(newState['pos'], update=False)
            self.prepareGeometryChange()
            self.state = newState
        
            self.updateHandles()
        
        self.handleChange()
    
    def handleChange(self):
        changed = False
        if self.lastState is None:
            changed = True
        else:
            for k in self.state.keys():
                if self.state[k] != self.lastState[k]:
                    #print "state %s has changed; emit signal" % k
                    changed = True
        self.lastState = self.stateCopy()
        if changed:
            self.update()
            self.emit(QtCore.SIGNAL('regionChanged'), self)
            
    
    def scale(self, s, center=[0,0]):
        c = self.mapToScene(Point(center) * self.state['size'])
        self.prepareGeometryChange()
        self.state['size'] = self.state['size'] * s
        c1 = self.mapToScene(Point(center) * self.state['size'])
        self.state['pos'] = self.state['pos'] + c - c1
        self.setPos(self.state['pos'])
        self.updateHandles()
    
    def translate(self, *args, **kargs):
        """accepts either (x, y, snap) or ([x,y], snap) as arguments"""
        if 'snap' not in kargs:
            snap = None
        else:
            snap = kargs['snap']

        if len(args) == 1:
            pt = args[0]
        else:
            pt = args
            
        newState = self.stateCopy()
        newState['pos'] = newState['pos'] + pt
        if snap != None:
            newState['pos'][0] = round(newState['pos'][0] / snap[0]) * snap[0]
            newState['pos'][1] = round(newState['pos'][1] / snap[1]) * snap[1]
            
        
        #d = ev.scenePos() - self.mapToScene(self.pressPos)
        if self.maxBounds is not None:
            r = self.stateRect(newState)
            #r0 = self.sceneTransform().mapRect(self.boundingRect())
            d = Point(0,0)
            if self.maxBounds.left() > r.left():
                d[0] = self.maxBounds.left() - r.left()
            elif self.maxBounds.right() < r.right():
                d[0] = self.maxBounds.right() - r.right()
            if self.maxBounds.top() > r.top():
                d[1] = self.maxBounds.top() - r.top()
            elif self.maxBounds.bottom() < r.bottom():
                d[1] = self.maxBounds.bottom() - r.bottom()
            newState['pos'] += d
        
        self.state['pos'] = newState['pos']
        self.setPos(self.state['pos'])
        #if 'update' not in kargs or kargs['update'] is True:
        self.handleChange()
    
    def stateRect(self, state):
        r = QtCore.QRectF(0, 0, state['size'][0], state['size'][1])
        tr = QtGui.QTransform()
        tr.rotate(-state['angle'] * 180 / pi)
        r = tr.mapRect(r)
        return r.adjusted(state['pos'][0], state['pos'][1], state['pos'][0], state['pos'][1])
    
    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.state['size'][0], self.state['size'][1])

    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.pen)
        p.drawRect(r)
        

    def getArraySlice(self, data, img, axes=(0,1), returnSlice=True):
        """Return a tuple of slice objects that can be used to slice the region from data covered by this ROI.
        Also returns the transform which maps the ROI into data coordinates.
        
        If returnSlice is set to False, the function returns a pair of tuples with the values that would have 
        been used to generate the slice objects. ((ax0Start, ax0Stop), (ax1Start, ax1Stop))"""
        #print "getArraySlice"
        
        ## Determine shape of array along ROI axes
        dShape = (data.shape[axes[0]], data.shape[axes[1]])
        #print "  dshape", dShape
        
        ## Determine transform that maps ROI bounding box to image coordinates
        tr = self.sceneTransform() * img.sceneTransform().inverted()[0] 
        
        ## Modify transform to scale from image coords to data coords
        #m = QtGui.QTransform()
        tr.scale(float(dShape[0]) / img.width(), float(dShape[1]) / img.height())
        #tr = tr * m
        
        ## Transform ROI bounds into data bounds
        dataBounds = tr.mapRect(self.boundingRect())
        #print "  boundingRect:", self.boundingRect()
        #print "  dataBounds:", dataBounds
        
        ## Intersect transformed ROI bounds with data bounds
        intBounds = dataBounds.intersect(QtCore.QRectF(0, 0, dShape[0], dShape[1]))
        #print "  intBounds:", intBounds
        
        ## Determine index values to use when referencing the array. 
        bounds = (
            (int(min(intBounds.left(), intBounds.right())), int(1+max(intBounds.left(), intBounds.right()))),
            (int(min(intBounds.bottom(), intBounds.top())), int(1+max(intBounds.bottom(), intBounds.top())))
        )
        #print "  bounds:", bounds
        
        if returnSlice:
            ## Create slice objects
            sl = [slice(None)] * data.ndim
            sl[axes[0]] = slice(*bounds[0])
            sl[axes[1]] = slice(*bounds[1])
            return tuple(sl), tr
        else:
            return bounds, tr


    def getArrayRegion(self, data, img, axes=(0,1)):
        
        ## transpose data so x and y are the first 2 axes
        trAx = range(0, data.ndim)
        trAx.remove(axes[0])
        trAx.remove(axes[1])
        tr1 = tuple(axes) + tuple(trAx)
        arr = data.transpose(tr1)
        
        ## Determine the minimal area of the data we will need
        (dataBounds, roiDataTransform) = self.getArraySlice(data, img, returnSlice=False, axes=axes)

        ## Pad data boundaries by 1px if possible
        dataBounds = (
            (max(dataBounds[0][0]-1, 0), min(dataBounds[0][1]+1, arr.shape[0])),
            (max(dataBounds[1][0]-1, 0), min(dataBounds[1][1]+1, arr.shape[1]))
        )

        ## Extract minimal data from array
        arr1 = arr[dataBounds[0][0]:dataBounds[0][1], dataBounds[1][0]:dataBounds[1][1]]
        
        ## Update roiDataTransform to reflect this extraction
        roiDataTransform *= QtGui.QTransform().translate(-dataBounds[0][0], -dataBounds[1][0]) 
        ### (roiDataTransform now maps from ROI coords to extracted data coords)
        
        
        ## Rotate array
        if abs(self.state['angle']) > 1e-5:
            arr2 = ndimage.rotate(arr1, self.state['angle'] * 180 / pi, order=1)
            
            ## update data transforms to reflect this rotation
            rot = QtGui.QTransform().rotate(self.state['angle'] * 180 / pi)
            roiDataTransform *= rot
            
            ## The rotation also causes a shift which must be accounted for:
            dataBound = QtCore.QRectF(0, 0, arr1.shape[0], arr1.shape[1])
            rotBound = rot.mapRect(dataBound)
            roiDataTransform *= QtGui.QTransform().translate(-rotBound.left(), -rotBound.top())
            
        else:
            arr2 = arr1
        
        
        
        ### Shift off partial pixels
        # 1. map ROI into current data space
        roiBounds = roiDataTransform.mapRect(self.boundingRect())
        
        # 2. Determine amount to shift data
        shift = (int(roiBounds.left()) - roiBounds.left(), int(roiBounds.bottom()) - roiBounds.bottom())
        if abs(shift[0]) > 1e-6 or abs(shift[1]) > 1e-6:
            # 3. pad array with 0s before shifting
            arr2a = zeros((arr2.shape[0]+2, arr2.shape[1]+2) + arr2.shape[2:], dtype=arr2.dtype)
            arr2a[1:-1, 1:-1] = arr2
            
            # 4. shift array and udpate transforms
            arr3 = ndimage.shift(arr2a, shift + (0,)*(arr2.ndim-2), order=1)
            roiDataTransform *= QtGui.QTransform().translate(1+shift[0], 1+shift[1]) 
        else:
            arr3 = arr2
        
        
        ### Extract needed region from rotated/shifted array
        # 1. map ROI into current data space (round these values off--they should be exact integer values at this point)
        roiBounds = roiDataTransform.mapRect(self.boundingRect())
        #print self, roiBounds.height()
        #import traceback
        #traceback.print_stack()
        
        roiBounds = QtCore.QRect(round(roiBounds.left()), round(roiBounds.top()), round(roiBounds.width()), round(roiBounds.height()))
        
        #2. intersect ROI with data bounds
        dataBounds = roiBounds.intersect(QtCore.QRect(0, 0, arr3.shape[0], arr3.shape[1]))
        
        #3. Extract data from array
        db = dataBounds
        bounds = (
            (db.left(), db.right()+1),
            (db.top(), db.bottom()+1)
        )
        arr4 = arr3[bounds[0][0]:bounds[0][1], bounds[1][0]:bounds[1][1]]

        ### Create zero array in size of ROI
        arr5 = zeros((roiBounds.width(), roiBounds.height()) + arr4.shape[2:], dtype=arr4.dtype)
        
        ## Fill array with ROI data
        orig = Point(dataBounds.topLeft() - roiBounds.topLeft())
        subArr = arr5[orig[0]:orig[0]+arr4.shape[0], orig[1]:orig[1]+arr4.shape[1]]
        subArr[:] = arr4[:subArr.shape[0], :subArr.shape[1]]
        
        
        ## figure out the reverse transpose order
        tr2 = array(tr1)
        for i in range(0, len(tr2)):
            tr2[tr1[i]] = i
        tr2 = tuple(tr2)
        
        ## Untranspose array before returning
        return arr5.transpose(tr2)





        

class Handle(QtGui.QGraphicsItem):
    def __init__(self, radius, typ=None, pen=QtGui.QPen(QtGui.QColor(200, 200, 220)), parent=None):
        #print "   create item with parent", parent
        QtGui.QGraphicsItem.__init__(self, parent)
        self.setZValue(11)
        self.roi = []
        self.radius = radius
        self.typ = typ
        self.bounds = QtCore.QRectF(-1e-10, -1e-10, 2e-10, 2e-10)
        self.pen = pen
        if typ == 't':
            self.sides = 4
            self.startAng = pi/4
        elif typ == 's':
            self.sides = 4
            self.startAng = 0
        elif typ == 'r':
            self.sides = 12
            self.startAng = 0
        elif typ == 'sr':
            self.sides = 12
            self.startAng = 0
        else:
            self.sides = 4
            self.startAng = pi/4
            
    def connectROI(self, roi, i):
        self.roi.append((roi, i))
    
    def boundingRect(self):
        return self.bounds
        
    def mousePressEvent(self, ev):
        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
            return
        self.cursorOffset = self.scenePos() - ev.scenePos()
        for r in self.roi:
            r[0].pointPressEvent(r[1], ev)
        ev.accept()
        
    def mouseReleaseEvent(self, ev):
        #print "release"
        for r in self.roi:
            r[0].pointReleaseEvent(r[1], ev)
                
    def mouseMoveEvent(self, ev):
        #print "handle mouseMove", ev.pos()
        pos = ev.scenePos() + self.cursorOffset
        self.movePoint(pos, ev.modifiers())
        
    def movePoint(self, pos, modifiers=QtCore.Qt.KeyboardModifier()):
        for r in self.roi:
            if not r[0].checkPointMove(r[1], pos, modifiers):
                return
        #print "point moved; inform %d ROIs" % len(self.roi)
        for r in self.roi:
            r[0].movePoint(r[1], pos, modifiers)
        
    def paint(self, p, opt, widget):
        m = p.transform()
        mi = m.inverted()[0]
        size = mi.map(Point(self.radius, self.radius)) - mi.map(Point(0, 0))
        size = (size.x()*size.x() + size.y() * size.y()) ** 0.5
        bounds = QtCore.QRectF(-size, -size, size*2, size*2)
        if bounds != self.bounds:
            self.bounds = bounds
            self.prepareGeometryChange()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.pen)
        ang = self.startAng
        dt = 2*pi / self.sides
        for i in range(0, self.sides):
            x1 = size * cos(ang)
            y1 = size * sin(ang)
            x2 = size * cos(ang+dt)
            y2 = size * sin(ang+dt)
            ang += dt
            p.drawLine(Point(x1, y1), Point(x2, y2))
        




class TestROI(ROI):
    def __init__(self, pos, size, **args):
        #QtGui.QGraphicsRectItem.__init__(self, pos[0], pos[1], size[0], size[1])
        ROI.__init__(self, pos, size, **args)
        #self.addTranslateHandle([0, 0])
        self.addTranslateHandle([0.5, 0.5])
        self.addScaleHandle([1, 1], [0, 0])
        self.addScaleHandle([0, 0], [1, 1])
        self.addScaleRotateHandle([1, 0.5], [0.5, 0.5])
        self.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.addRotateHandle([1, 0], [0, 0])
        self.addRotateHandle([0, 1], [1, 1])



class RectROI(ROI):
    def __init__(self, pos, size, centered=False, sideScalers=False, **args):
        #QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        ROI.__init__(self, pos, size, **args)
        if centered:
            center = [0.5, 0.5]
        else:
            center = [0, 0]
            
        #self.addTranslateHandle(center)
        self.addScaleHandle([1, 1], center)
        if sideScalers:
            self.addScaleHandle([1, 0.5], [center[0], 0.5])
            self.addScaleHandle([0.5, 1], [0.5, center[1]])

class LineROI(ROI):
    def __init__(self, pos1, pos2, width, **args):
        pos1 = Point(pos1)
        pos2 = Point(pos2)
        d = pos2-pos1
        l = d.length()
        ang = Point(1, 0).angle(d)
        c = Point(-width/2. * sin(ang), -width/2. * cos(ang))
        pos1 = pos1 + c
        
        ROI.__init__(self, pos1, size=Point(l, width), angle=ang*180/pi, **args)
        self.addScaleRotateHandle([0, 0.5], [1, 0.5])
        self.addScaleRotateHandle([1, 0.5], [0, 0.5])
        self.addScaleHandle([0.5, 1], [0.5, 0.5])
        
        
class MultiLineROI(QtGui.QGraphicsItem, QObjectWorkaround):
    def __init__(self, points, width, **args):
        QObjectWorkaround.__init__(self)
        QtGui.QGraphicsItem.__init__(self)
        self.roiArgs = args
        if len(points) < 2:
            raise Exception("Must start with at least 2 points")
        self.lines = []
        self.lines.append(ROI([0, 0], [1, 5], parent=self))
        self.lines[-1].addScaleHandle([0.5, 1], [0.5, 0.5])
        h = self.lines[-1].addScaleRotateHandle([0, 0.5], [1, 0.5])
        h.movePoint(points[0])
        h.movePoint(points[0])
        for i in range(1, len(points)):
            h = self.lines[-1].addScaleRotateHandle([1, 0.5], [0, 0.5])
            if i < len(points)-1:
                self.lines.append(ROI([0, 0], [1, 5], parent=self))
                self.lines[-1].addScaleRotateHandle([0, 0.5], [1, 0.5], item=h)
            h.movePoint(points[i])
            h.movePoint(points[i])
            
        for l in self.lines:
            l.translatable = False
            #self.addToGroup(l)
            l.connect(QtCore.SIGNAL('regionChanged'), self.roiChangedEvent)
            l.connect(QtCore.SIGNAL('regionChangeStarted'), self.roiChangeStartedEvent)
            l.connect(QtCore.SIGNAL('regionChangeFinished'), self.roiChangeFinishedEvent)
        
    def paint(self, *args):
        pass
    
    def boundingRect(self):
        return QtCore.QRectF()
        
    def roiChangedEvent(self):
        w = self.lines[0].state['size'][1]
        for l in self.lines[1:]:
            w0 = l.state['size'][1]
            l.scale([1.0, w/w0], center=[0.5,0.5])
        self.emit(QtCore.SIGNAL('regionChanged'), self)
            
    def roiChangeStartedEvent(self):
        self.emit(QtCore.SIGNAL('regionChangeStarted'), self)
        
    def roiChangeFinishedEvent(self):
        self.emit(QtCore.SIGNAL('regionChangeFinished'), self)
        
            
    def getArrayRegion(self, arr, img=None):
        rgns = []
        for l in self.lines:
            rgn = l.getArrayRegion(arr, img)
            if rgn is None:
                continue
                #return None
            rgns.append(rgn)
            #print l.state['size']
        #print [(r.shape) for r in rgns]
        return vstack(rgns)
        
        
class EllipseROI(ROI):
    def __init__(self, pos, size, **args):
        #QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        ROI.__init__(self, pos, size, **args)
        self.addRotateHandle([1.0, 0.5], [0.5, 0.5])
        self.addScaleHandle([0.5*2.**-0.5 + 0.5, 0.5*2.**-0.5 + 0.5], [0.5, 0.5])
            
    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.pen)
        
        p.scale(r.width(), r.height())## workaround for GL bug
        r = QtCore.QRectF(r.x()/r.width(), r.y()/r.height(), 1,1)
        
        p.drawEllipse(r)
        
    def getArrayRegion(self, arr, img=None):
        arr = ROI.getArrayRegion(self, arr, img)
        if arr is None or arr.shape[0] == 0 or arr.shape[1] == 0:
            return None
        w = arr.shape[0]
        h = arr.shape[1]
        ## generate an ellipsoidal mask
        mask = fromfunction(lambda x,y: (((x+0.5)/(w/2.)-1)**2+ ((y+0.5)/(h/2.)-1)**2)**0.5 < 1, (w, h))
    
        return arr * mask
    
    def shape(self):
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path
        
        
class CircleROI(EllipseROI):
    def __init__(self, pos, size, **args):
        ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True
        #self.addTranslateHandle([0.5, 0.5])
        self.addScaleHandle([0.5*2.**-0.5 + 0.5, 0.5*2.**-0.5 + 0.5], [0.5, 0.5])
        