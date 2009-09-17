# -*- coding: utf-8 -*-
from lib.modules.ProtocolRunner.analysisModules import AnalysisModule
from lib.Manager import getManager
from PyQt4 import QtCore, QtGui
from UncagingTemplate import Ui_Form
from lib.util.qtgraph.graphicsItems import ImageItem
from numpy import *
from scipy.ndimage.filters import gaussian_filter
from lib.util.MetaArray import MetaArray

class UncagingModule(AnalysisModule):
    def __init__(self, *args):
        AnalysisModule.__init__(self, *args)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.postGuiInit()
        self.man = getManager()
        mods = self.man.listModules()
        devs = self.man.listDevices()
        for m in mods:
            self.ui.cameraModCombo.addItem(m)
        for d in devs:
            self.ui.scannerDevCombo.addItem(d)
            self.ui.clampDevCombo.addItem(d)
        self.prots = {}
        self.currentProt = None
        QtCore.QObject.connect(self.ui.deleteBtn, QtCore.SIGNAL('clicked()'), self.deleteSelected)
        QtCore.QObject.connect(self.stateGroup, QtCore.SIGNAL('changed'), self.stateChanged)
        QtCore.QObject.connect(self.ui.protList, QtCore.SIGNAL('currentItemChanged(QListWidgetItem*, QListWidgetItem*)'), self.itemSelected)
        QtCore.QObject.connect(self.ui.protList, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'), self.itemClicked)
        QtCore.QObject.connect(self.ui.recomputeBtn, QtCore.SIGNAL('clicked()'), self.recompute)
        
        
    def protocolStarted(self, *args):
        #print "start:",args
        #self.newProt()
        pass
    
    def protocolFinished(self):
        self.currentProt = None
        
    def newFrame(self, frame):
        if not self.ui.enabledCheck.isChecked():
            return
        if self.currentProt is None:
            self.newProt()
        self.currentProt.addFrame(frame)

    def newProt(self):
        n = self.pr.currentProtocol.name()
        i = 0
        while True:
            name = n + ("_%03d" % i)
            if name not in self.prots:
                break
            i += 1
        p = Prot(name, self)
        self.currentProt = p
        self.prots[name] = p
        item = QtGui.QListWidgetItem(name)
        item.setCheckState(QtCore.Qt.Checked)
        self.ui.protList.addItem(item)
        self.ui.protList.setCurrentItem(item)

    def deleteSelected(self):
        row = self.ui.protList.currentRow()
        if row == -1:
            return
        item = self.ui.protList.takeItem(row)
        name = str(item.text())
        self.prots[name].close()
        del self.prots[name]
        if self.currentProt is not None and self.currentProt.name == name:
            self.currentProt = None
    
    def selectedProt(self):
        row = self.ui.protList.currentRow()
        if row == -1:
            return None
        item = self.ui.protList.item(row)
        name = str(item.text())
        return self.prots[name]
        
    
    def stateChanged(self, *args):
        sp = self.selectedProt()
        if sp is not None:
            sp.updateParams(*args)
            
    def itemSelected(self, *args):
        sp = self.selectedProt()
        if sp is not None:
            self.stateGroup.setState(sp.getState())
            
    def itemClicked(self, item):
        prot = self.prots[str(item.text())]
        if item.checkState() == QtCore.Qt.Checked:
            prot.show()
        else:
            prot.hide()

    def recompute(self):
        sp = self.selectedProt()
        if sp is not None:
            sp.recalculate(allFrames=True)

    def quit(self):
        AnalysisModule.quit(self)
        for p in self.prots.values():
            p.close()
            
    def cameraModule(self):
        return str(self.ui.cameraModCombo.currentText())
        
    def cameraDevice(self):
        camMod = self.cameraModule()
        mod = self.man.getModule(camMod)
        if 'camDev' in mod.config:
            return mod.config['camDev']
        else:
            return None

    def clampDevice(self):
        return str(self.ui.clampDevCombo.currentText())
        
    def scannerDevice(self):
        return str(self.ui.scannerDevCombo.currentText())
        
        
class Prot:
    z = 500
    params = ['alphaSlider', 'frame1Spin', 'frame2Spin', 'clampBaseStartSpin', 'clampBaseStopSpin', 'clampTestStartSpin', 'clampTestStopSpin', 'pspToleranceSpin', 'spotToleranceSpin', 'displayImageCheck']
    
    def __init__(self, name, ui):
        self.name = name
        self.ui = ui
        self.frames = []
        self.imgItem = ImageItem()
        self.items = [[self.imgItem, [0,0], [1,1]]]
        self.img = None
        self.updateParams()
        self.z = Prot.z
        Prot.z += 1
        
    def addFrame(self, frame):
        camDev = self.ui.cameraDevice()
        clampDev = self.ui.clampDevice()
        scannerDev = self.ui.scannerDevice()
        
        scanUi = self.ui.pr.getDevice(scannerDev)
        pointSize = scanUi.pointSize()
        
        camFrame1 = frame['result'][camDev]['frames'][self.state['frame1Spin']]
        camFrame2 = frame['result'][camDev]['frames'][self.state['frame2Spin']]
        camFrame = MetaArray(camFrame2.astype(float32) - camFrame1.astype(float32), info=camFrame1.infoCopy())
        data = {
            'cam': camFrame,
            'clamp': frame['result'][clampDev]['scaled'].copy(),
            'scanner': frame['result'][scannerDev]
        }
        data['scanner']['spot'] = pointSize
        #print "============\n", data
        #print "New frame:", data['clamp'].shape, data['clamp'].xvals('Time').shape
        self.frames.append(data)
        self.recalculate()
        
    def updateParams(self, param=None, val=None):
        state = self.ui.stateGroup.state().copy()
        self.state = {}
        for k in Prot.params:
            self.state[k] = state[k]
        if param == 'alphaSlider':
            self.updateAlpha()
            #self.imgItem.setAlpha(state['alphaSlider'])
        #else:
            #self.recalculate(allFrames=True)

    def updateAlpha(self):
        if self.state['displayImageCheck']:
            self.updateImage()
        else:
            for (i, p, s) in self.items[1:]:
                c = i.brush().color()
                c.setAlpha(self.state['alphaSlider'])
                i.setBrush(QtGui.QBrush(c))
            

    def recalculate(self, allFrames=False):
        if len(self.frames) < 1:
            return
        #print "recalc", allFrames
        #print self.state
        ## calculate image
        if allFrames:
            ## Clear out old displays
            self.img = None
            for (i, p, s) in self.items[1:]:
                s = i.scene()
                if s is not None:
                    s.removeItem(i)
            self.items = self.items[:1]
            
            ## Compute for all frames
            frames = self.frames
        else:
            frames = self.frames[-1:]
        
        if self.img is None:
            self.img = zeros(frames[0]['cam'].shape + (4,), dtype=float32)
        
        for f in frames:
            (r, g, b) = self.evaluateTrace(f['clamp'])
            
            if self.state['displayImageCheck']:
                alpha = gaussian_filter((f['cam'] - f['cam'].min()), (5, 5))
                tol = self.state['spotToleranceSpin']
                alpha = clip(alpha-tol, 0, 2**32)
                alpha *= 256. / alpha.max()
                newImg = empty(frames[0]['cam'].shape + (4,), dtype=uint16)
                newImg[..., 0] = b * alpha
                newImg[..., 1] = g * alpha
                newImg[..., 2] = r * alpha
                newImg[..., 3] = alpha
                
                self.img = clip(self.img + (newImg.astype(uint16)), 0, 255)
            else:
                alpha = self.state['alphaSlider']
                spot = QtGui.QGraphicsEllipseItem(QtCore.QRectF(-0.5, -0.5, 1, 1))
                spot.setBrush(QtGui.QBrush(QtGui.QColor(r*255, g*255, b*255, alpha)))
                spot.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                p = f['scanner']['position']
                s = f['scanner']['spot']
                self.items.append([spot, p, [s, s]])
            
        self.hide()  ## Make sure only correct items are displayed
        self.show()
        if self.state['displayImageCheck']:
            self.updateImage()
        info = frames[-1]['cam'].infoCopy()[-1]
        s = info['pixelSize']
        p = info['imagePosition']
        self.items[0][1] = p
        self.items[0][2] = s
        
        ## Set correct scene
        cModName = str(self.ui.ui.cameraModCombo.currentText())
        camMod = self.ui.man.getModule(cModName)
        scene = camMod.ui.scene
        for i in self.items:
            (item, p, s) = i
            if item.scene() is not scene:
                camMod.ui.addItem(item, p, s, self.z)


    def updateImage(self):
        #print "updateImage", self.img.shape, self.img.max(axis=0).max(axis=0), self.img.min(axis=0).min(axis=0)
        #print "scene:", self.imgItem.scene(), "z", self.imgItem.zValue(), 'visible', self.imgItem.isVisible()
        aImg = self.img.astype(uint8)
        aImg[..., 3] *= float(self.state['alphaSlider']) / self.ui.ui.alphaSlider.maximum()
        self.imgItem.updateImage(aImg)

    def evaluateTrace(self, data):
        bstart = self.state['clampBaseStartSpin'] * 1e-3
        bstop = self.state['clampBaseStopSpin'] * 1e-3
        tstart = self.state['clampTestStartSpin'] * 1e-3
        tstop = self.state['clampTestStopSpin'] * 1e-3
        base = data['Time': bstart:bstop].view(ndarray)
        test = data['Time': tstart:tstop].view(ndarray)
        med = median(base)
        std = base.std()
        test = test - med
        g = 0.0
        tol = self.state['pspToleranceSpin']
        r = clip(test.max() / (tol*std), 0.0, 1.0)
        b = clip(-test.min() / (tol*std), 0.0, 1.0)
        
        ## measure latency 
        
        for i in range(5):
            t = i * 1e-3
            sec = data['Time': tstart+t:tstart+t+1e-3].view(ndarray)
            if (abs(sec.max()-med) > tol*std) or (abs(sec.min()-med) > tol*std):
                g = (5-i) * 0.2
                break

        g = clip(g, 0.0, 1.0)
        return (r, g, b)
        
        
    def __del__(self):
        self.close()
    
    def getState(self):
        return self.state
        
    def show(self):
        #self.visible = True
        if self.state['displayImageCheck']:
            self.imgItem.show()
        else:
            for (i, p, s) in self.items[1:]:
                i.show()
        
    def hide(self):
        #self.visible = False
        for (i, p, s) in self.items:
            i.hide()
        
    def close(self):
        ## Remove items from scene
        for (item, p, s) in self.items:
            scene = item.scene()
            if scene is not None:
                scene.removeItem(item)
                
        