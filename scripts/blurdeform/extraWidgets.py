from __future__ import print_function
from __future__ import absolute_import
from maya import OpenMaya, OpenMayaMPx, OpenMayaUI, cmds, mel
from Qt import QtWidgets, QtCore, QtGui
import blurdev
import sip
import time, datetime


# create a QtObject for not using  sip.wrapinstance too much
def getQTObject():
    if not cmds.window("tmpWidgetsWindow", q=True, ex=True):
        cmds.window("tmpWidgetsWindow")
        cmds.formLayout("qtLayoutObjects")
    mayaWindow = blurdev.core.rootWindow()
    for ind, el in enumerate(mayaWindow.children()):
        try:
            title = el.windowTitle()
            if title == "tmpWidgetsWindow":
                break
        except:
            continue
    return el


class toggleBlockSignals(object):
    def __init__(self, listWidgets, raise_error=True):
        self.listWidgets = listWidgets

    def __enter__(self):
        for widg in self.listWidgets:
            widg.blockSignals(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for widg in self.listWidgets:
            widg.blockSignals(False)


# spinner connected to an attribute
class spinnerWidget(QtWidgets.QWidget):
    def offsetSpin_mousePressEvent(self, event):
        theAttrs = self.theAttr if isinstance(self.theAttr, list) else [self.theAttr]
        for theAttr in theAttrs:
            if cmds.objExists(theAttr):
                val = cmds.getAttr(theAttr)
                self.theSpinner.setValue(val)
                QtWidgets.QDoubleSpinBox.mousePressEvent(self.theSpinner, event)

    def offsetSpin_wheelEvent(self, event):
        theAttrs = self.theAttr if isinstance(self.theAttr, list) else [self.theAttr]
        for theAttr in theAttrs:
            if cmds.objExists(theAttr):
                val = cmds.getAttr(theAttr)
                self.theSpinner.setValue(val)
                QtWidgets.QDoubleSpinBox.wheelEvent(self.theSpinner, event)

    def valueChangedFn(self, newVal):
        theAttrs = self.theAttr if isinstance(self.theAttr, list) else [self.theAttr]
        for theAttr in theAttrs:
            if cmds.objExists(theAttr) and cmds.getAttr(theAttr, settable=True):
                cmds.setAttr(theAttr, newVal)

    def createWidget(self, singleStep=0.1, precision=2):
        theWindowForQtObjects = getQTObject()

        cmds.setParent("tmpWidgetsWindow|qtLayoutObjects")
        self.floatField = cmds.floatField(pre=precision, step=singleStep)

        self.theQtObject = theWindowForQtObjects.children()[-1]
        """
        if qtLayoutObject :
            self.theQtObject = qtLayoutObject
        else : 
            self.theQtObject = toQtObject (self.floatField)
        """

        self.theQtObject.setParent(self)
        self.theSpinner.lineEdit().hide()
        self.theQtObject.move(self.theSpinner.pos())
        self.theQtObject.show()

        self.theSpinner.valueChanged.connect(self.valueChangedFn)
        # set before click
        self.theSpinner.mousePressEvent = self.offsetSpin_mousePressEvent
        # set before spin
        self.theSpinner.wheelEvent = self.offsetSpin_wheelEvent
        self.theSpinner.resize(self.size())
        wdth = self.theSpinner.lineEdit().width() + 3
        self.theQtObject.resize(wdth, self.height())

    def doConnectAttrSpinner(self, theAttr):
        # print theAttr
        self.theAttr = theAttr
        if isinstance(self.theAttr, list):
            theAttr = self.theAttr[0]
        if cmds.objExists(theAttr):
            cmds.connectControl(self.floatField, theAttr)
            minValue, maxValue = -16777214, 16777215

            listAtt = theAttr.split(".")
            att = listAtt[-1]
            node = ".".join(listAtt[:-1])

            if cmds.attributeQuery(att, node=node, maxExists=True):
                (maxValue,) = cmds.attributeQuery(att, node=node, maximum=True)
            if cmds.attributeQuery(att, node=node, minExists=True):
                (minValue,) = cmds.attributeQuery(att, node=node, minimum=True)

            self.theSpinner.setRange(minValue, maxValue)

    def resizeEvent(self, event):
        self.theSpinner.resize(self.size())
        wdth = self.theSpinner.lineEdit().width() + 3
        self.theQtObject.resize(wdth, self.height())

    def __init__(self, theAttr, singleStep=0.1, precision=2):
        super(spinnerWidget, self).__init__()
        self.theAttr = theAttr
        self.theSpinner = QtWidgets.QDoubleSpinBox(self)
        self.theSpinner.setRange(-16777214, 16777215)
        self.theSpinner.setSingleStep(singleStep)
        self.theSpinner.setDecimals(precision)

        self.theSpinner.move(0, 0)
        # self.setMinimumWidth(50)
        self.createWidget(singleStep=singleStep, precision=precision)
        self.doConnectAttrSpinner(theAttr)


class KeyFrameBtn(QtWidgets.QPushButton):
    _colors = {
        "redColor": "background-color: rgb(154, 10, 10);",
        "redLightColor": "background-color: rgb(255, 153, 255);",
        "blueColor": "background-color: rgb(10, 10, 154);",
        "blueLightColor": "background-color: rgb(153,255, 255);",
    }
    pressedColor = "background-color: rgb(255, 255, 255);"

    def delete(self):
        self.theTimeSlider.listKeys.remove(self)
        sip.delete(self)

    def mouseMoveEvent(self, event):
        # print "begin  mouseMove event"

        controlShitPressed = (
            event.modifiers() == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
        )
        shiftPressed = (
            controlShitPressed
            or event.modifiers() == QtCore.Qt.KeyboardModifiers(QtCore.Qt.ShiftModifier)
        )

        Xpos = event.globalX() - self.globalX + self.prevPos.x()
        theKey = (Xpos - self.startPos) / self.oneKeySize
        if not shiftPressed:
            theKey = int(theKey)
        theTime = theKey + self.startpb

        if theTime < self.start:
            theTime = self.start
        elif theTime > self.end:
            theTime = self.end

        if shiftPressed:
            self.theTime = round(theTime, 3)
        else:
            self.theTime = int(theTime)
        self.updatePosition()

        # print "end  mouseMove event"
        super(KeyFrameBtn, self).mouseMoveEvent(event)

    def mousePressEvent(self, event):
        # print "begin  mousePress event"
        controlShitPressed = (
            event.modifiers() == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
        )
        controlPressed = (
            controlShitPressed or event.modifiers() == QtCore.Qt.ControlModifier
        )
        shiftPressed = (
            controlShitPressed
            or event.modifiers() == QtCore.Qt.KeyboardModifiers(QtCore.Qt.ShiftModifier)
        )

        if shiftPressed:
            offsetKey = 0.001
        else:
            offsetKey = 1

        self.duplicateMode = controlPressed

        if not self.checked:
            self.select(addSel=controlPressed)
        if event.button() == QtCore.Qt.RightButton:
            index = self.theTimeSlider.listKeys.index(self)
            itemFrame = self.mainWindow.uiFramesTW.topLevelItem(index)

            self.mainWindow.clickedItem = itemFrame
            self.mainWindow.popup_menu.exec_(event.globalPos())

        elif event.button() == QtCore.Qt.LeftButton:

            self.globalX = event.globalX()
            self.prevPos = self.pos()
            self.prevTime = self.theTime

            startpb = cmds.playbackOptions(q=True, minTime=True)
            endpb = cmds.playbackOptions(q=True, maxTime=True)

            self.startPos = self.theTimeSlider.width() / 100.0 * 0.5
            self.oneKeySize = (self.theTimeSlider.width() - self.startPos * 2.0) / (
                endpb - startpb + 1.0
            )

            self.setStyleSheet(self.pressedColor)

            # self.mainWindow.listKeysToMove = [(el, el.theTime) for el in self.theTimeSlider.getSortedListKeysObj() if el.checked ]

            self.start = startpb
            self.end = endpb
            self.startpb = startpb

            if self.duplicateMode:
                self.theTimeSlider.addDisplayKey(self.prevTime, isEmpty=self.isEmpty)

            """
            super (KeyFrameBtn, self ).mousePressEvent (event)
        else : 
            super (KeyFrameBtn, self ).mousePressEvent (event)
            """
        # print "end mousePress event"

    def mouseReleaseEvent(self, event):
        super(KeyFrameBtn, self).mouseReleaseEvent(event)
        if self.prevTime != self.theTime:

            if self.duplicateMode:
                self.mainWindow.duplicateFrame(self.prevTime, self.theTime)
            else:
                # poseName = cmds.getAttr (self.mainWindow.currentPose+".poseName")
                # listDeformationsFrame = cmds.blurSculpt (self.mainWindow.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) )
                listDeformationsFrame = self.mainWindow.getListDeformationFrames()

                if self.theTime in listDeformationsFrame:
                    self.mainWindow.refresh()
                else:
                    cmds.undoInfo(undoName="moveSeveralKeys", openChunk=True)
                    self.updatePosition()
                    cmds.evalDeferred(self.doChangeTime)
                    cmds.undoInfo(undoName="moveSeveralKeys", closeChunk=True)

    def doChangeTime(self):
        index = self.theTimeSlider.listKeys.index(self)
        itemFrame = self.mainWindow.uiFramesTW.topLevelItem(index)
        itemFrame.setText(0, str(self.theTime))
        # check if refresh is necessary
        self.mainWindow.refreshListFramesAndSelect(self.theTime)

    def enterEvent(self, event):
        super(KeyFrameBtn, self).enterEvent(event)
        self.setFocus()
        self.setStyleSheet(self.lightColor)

    def leaveEvent(self, event):
        super(KeyFrameBtn, self).leaveEvent(event)

        if self.checked:
            self.setStyleSheet(self.lightColor)
        else:
            self.setStyleSheet(self.baseColor)

    def select(self, addSel=False, selectInTree=True):
        if not addSel:
            for el in self.theTimeSlider.listKeys:
                el.checked = False
                el.setStyleSheet(el.baseColor)
        self.checked = True
        cmds.evalDeferred(self.setFocus)

        # select in parent :
        if selectInTree:
            with toggleBlockSignals([self.mainWindow.uiFramesTW]):
                index = self.theTimeSlider.listKeys.index(self)
                itemFrame = self.mainWindow.uiFramesTW.topLevelItem(index)
                self.mainWindow.uiFramesTW.setCurrentItem(itemFrame)
        self.setStyleSheet(self.lightColor)

    def updatePosition(self, startPos=None, oneKeySize=None, start=None, end=None):
        if start == None or end == None:
            start = cmds.playbackOptions(q=True, minTime=True)
            end = cmds.playbackOptions(q=True, maxTime=True)

        isVisible = self.theTime >= start and self.theTime <= end

        self.setVisible(isVisible)
        if isVisible:
            if oneKeySize == None or startPos == None:
                theTimeSlider_width = self.theTimeSlider.width()
                startPos = theTimeSlider_width / 100.0 * 0.5
                oneKeySize = (theTimeSlider_width - startPos * 2.0) / (
                    end - start + 1.0
                )

            Xpos = (self.theTime - start) * oneKeySize + startPos
            self.move(Xpos, 15)
            if oneKeySize < 6:
                self.resize(6, 40)
            else:
                self.resize(oneKeySize, 40)

    def __init__(self, theTime, theTimeSlider, isEmpty=False):
        super(KeyFrameBtn, self).__init__(None)
        self.checked = False
        if isEmpty:
            self.baseColor = self._colors["blueColor"]
            self.lightColor = self._colors["blueLightColor"]
        else:
            self.baseColor = self._colors["redColor"]
            self.lightColor = self._colors["redLightColor"]

        self.isEmpty = isEmpty
        self.duplicateMode = False

        self.setCursor(QtGui.QCursor(QtCore.Qt.SplitHCursor))
        if theTime == int(theTime):
            self.theTime = int(theTime)
        else:
            self.theTime = theTime

        self.theTimeSlider = theTimeSlider
        self.mainWindow = theTimeSlider.mainWindow

        self.setParent(self.theTimeSlider)
        self.resize(6, 40)
        self.setStyleSheet(self.baseColor)

        cmds.evalDeferred(self.updatePosition)
        self.show()


class TheTimeSlider(QtWidgets.QWidget):
    def deleteKeys(self):
        # print "deleteKeys"
        toDelete = [] + self.listKeys
        for keyFrameBtn in toDelete:
            keyFrameBtn.delete()
        self.listKeys = []

    def getSortedListKeysObj(self):
        return sorted(self.listKeys, key=lambda ky: ky.theTime)

    def addDisplayKey(self, theTime, isEmpty=False):
        keyFrameBtn = KeyFrameBtn(theTime, self, isEmpty=isEmpty)
        self.listKeys.append(keyFrameBtn)
        return keyFrameBtn

    def updateKeys(self):
        # print "updateKeys"
        listKeys = self.getSortedListKeysObj()
        listKeys.reverse()
        theTimeSlider_width = self.width()

        start = cmds.playbackOptions(q=True, minTime=True)
        end = cmds.playbackOptions(q=True, maxTime=True)
        startPos = theTimeSlider_width / 100.0 * 0.5
        oneKeySize = (theTimeSlider_width - startPos * 2.0) / (end - start + 1.0)

        for keyObj in listKeys:
            keyObj.updatePosition(
                startPos=startPos, oneKeySize=oneKeySize, start=start, end=end
            )

    def resizeEvent(self, e):
        self.theTimePort.resize(e.size().width(), 30)
        self.updateKeys()
        super(TheTimeSlider, self).resizeEvent(e)

    def __init__(self, mainWindow):
        super(TheTimeSlider, self).__init__(None)
        self.mainWindow = mainWindow

        self.listKeys = []
        # self.theTimePort = timePort.theTimePort
        # self.mayaMainWindow = timePort.mayaWindowLayout

        theWindowForQtObjects = getQTObject()
        cmds.setParent("tmpWidgetsWindow|qtLayoutObjects")
        # cmds.setParent ("MayaWindow|formLayout1|qtLayoutObjects")
        cmdsTimePort = cmds.timePort(
            "skinFixingTimePort",
            w=10,
            h=20,
            snap=True,
            globalTime=True,
            enableBackground=True,
            bgc=[0.5, 0.5, 0.6],
        )
        # self.theTimePort = gui_utils.qtLayoutObject.children() [-1]
        self.theTimePort = theWindowForQtObjects.children()[-1]

        self.theTimePort.setParent(self)
        self.theTimePort.show()

        self.setMaximumHeight(40)
        self.setMinimumHeight(40)


class WaitCursorCtxt(object):
    def __init__(self, raise_error=True):
        self.raise_error = raise_error

    def __enter__(self):
        cmds.waitCursor(state=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if cmds.waitCursor(q=True, state=True):
            cmds.waitCursor(state=False)


"""

        theWindowForQtObjects = getQTObject ()

        cmds.setParent ("tmpWidgetsWindow|qtLayoutObjects")        
        # cmds.setParent ("MayaWindow|formLayout1|qtLayoutObjects")
        cmdsTimePort = cmds.timePort( 'skinFixingTimePort', w=10, h=20, snap=True, globalTime=True,enableBackground=True, bgc = [.5,.5,.6])
        # self.theTimePort = gui_utils.qtLayoutObject.children() [-1]                
        self.theTimePort = theWindowForQtObjects .children() [-1]  

        
        self.theTimePort.setParent (self)
"""


"""
from ilion_maya.gui_utils import lib as gui_utils
import time
nbValues = 100
with gui_utils.MayaProgressBar(maxValue=nbValues,  status="test ...", frontWindow=True) as pBar:
    for el in range (amountOfLoops):        
        if not pBar.update() : break
        time.sleep (.1)
"""
# maya progress bar
class MayaProgressBar(object):
    def __init__(
        self, maxValue=100, status="Processing...", frontWindow=True, QTprogress=None
    ):
        self.maxValue = maxValue
        self.status = status
        self.frontWindow = frontWindow
        self.startTime = time.time()
        self.QTprogress = QTprogress

    def __enter__(self):
        self.progressBar = [mel.eval("$tmp = $gMainProgressBar")]
        if self.frontWindow:
            self.wind = cmds.window(title=self.status, resizeToFitChildren=True)
            cmds.columnLayout()
            self.progressBar.append(cmds.progressBar(w=300))
            cmds.showWindow(self.wind)
        else:
            self.wind = None

        progressStartKwargs = {
            "e": True,
            "isInterruptable": True,
            "beginProgress": True,
            "status": self.status,
            "maxValue": self.maxValue,
        }
        for prg in self.progressBar:
            cmds.progressBar(prg, **progressStartKwargs)
            # Fix for hanging previous progress (force cancel it and restart)
            if cmds.progressBar(prg, query=True, isCancelled=True):
                cmds.progressBar(prg, e=1, endProgress=True)
                cmds.progressBar(prg, **progressStartKwargs)

        if self.QTprogress:
            self.QTprogressHiddenState = self.QTprogress.isHidden()
            if self.QTprogressHiddenState:
                self.QTprogress.show()
            self.QTprogress.setRange(0, self.maxValue)
        self.index = 0
        return self

    def setStatus(self, s):
        for prg in self.progressBar:
            cmds.progressBar(prg, e=1, status=s)
        if self.wind:
            cmds.window(self.wind, e=True, title=s)

    def update(self):
        self.index += 1
        if self.QTprogress:
            self.QTprogress.setValue(self.index)
        for prg in self.progressBar:
            cmds.progressBar(prg, e=1, step=1)
        if cmds.progressBar(self.progressBar[0], query=True, isCancelled=True):
            # raise RuntimeError("Process interrupted.")
            cmds.warning("Process interrupted!!")
            return False
        return True

    def __exit__(self, type, value, traceback):
        completionTime = time.time() - self.startTime
        timeRes = str(datetime.timedelta(seconds=int(completionTime))).split(":")
        result = "{0} hours {1} mins {2} secs".format(*timeRes)
        print(
            "{0} executed in {1} [{2:.2f} secs]".format(
                self.status, result, completionTime
            )
        )
        for prg in self.progressBar:
            cmds.progressBar(prg, e=1, endProgress=True)
        if self.wind:
            cmds.deleteUI(self.wind)

        if self.QTprogress:
            self.QTprogress.setValue(0)
            if self.QTprogressHiddenState:
                self.QTprogress.hide()
