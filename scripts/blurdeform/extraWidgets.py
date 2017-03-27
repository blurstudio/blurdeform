from maya import OpenMaya, OpenMayaMPx, OpenMayaUI, cmds, mel
from PyQt4 import QtGui, QtCore
import blurdev


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


# spinner connected to an attribute
class spinnerWidget(QtGui.QWidget):
    def offsetSpin_mousePressEvent(self, event):
        if cmds.objExists(self.theAttr):
            val = cmds.getAttr(self.theAttr)
            self.theSpinner.setValue(val)
            QtGui.QDoubleSpinBox.mousePressEvent(self.theSpinner, event)

    def offsetSpin_wheelEvent(self, event):
        if cmds.objExists(self.theAttr):
            val = cmds.getAttr(self.theAttr)
            self.theSpinner.setValue(val)
            QtGui.QDoubleSpinBox.wheelEvent(self.theSpinner, event)

    def valueChangedFn(self, newVal):
        if cmds.objExists(self.theAttr) and cmds.getAttr(self.theAttr, settable=True):
            cmds.setAttr(self.theAttr, newVal)

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

        QtCore.QObject.connect(
            self.theSpinner, QtCore.SIGNAL("valueChanged(double)"), self.valueChangedFn
        )
        # set before click
        self.theSpinner.mousePressEvent = self.offsetSpin_mousePressEvent
        # set before spin
        self.theSpinner.wheelEvent = self.offsetSpin_wheelEvent
        self.theSpinner.resize(self.size())
        wdth = self.theSpinner.lineEdit().width() + 3
        self.theQtObject.resize(wdth, self.height())

    def doConnectAttrSpinner(self, theAttr):
        self.theAttr = theAttr
        if cmds.objExists(self.theAttr):
            cmds.connectControl(self.floatField, self.theAttr)
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
        self.theSpinner = QtGui.QDoubleSpinBox(self)
        self.theSpinner.setRange(-16777214, 16777215)
        self.theSpinner.setSingleStep(singleStep)
        self.theSpinner.setDecimals(precision)

        self.theSpinner.move(0, 0)
        # self.setMinimumWidth(50)
        self.createWidget(singleStep=singleStep, precision=precision)
        self.doConnectAttrSpinner(theAttr)


class KeyFrameBtn(QtGui.QPushButton):
    redColor = "background-color: rgb(154, 10, 10);"
    redLightColor = "background-color: #FF99FF;"
    pressedColor = "background-color: rgb(255, 255, 255);"

    def delete(self):
        self.theTimeSlider.listKeys.remove(self)
        sip.delete(self)
        """                    
        shiboken.delete(self.band)
        shiboken.delete(self)
        """

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

        if not self.checked:
            self.select(addSel=controlPressed)
        if event.button() == QtCore.Qt.RightButton:
            self.mainWindow.currentKey = self
            self.mainWindow.popMenu.exec_(event.globalPos())
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
            super(KeyFrameBtn, self).mousePressEvent(event)
        else:
            super(KeyFrameBtn, self).mousePressEvent(event)
        # print "end mousePress event"

    def mouseReleaseEvent(self, event):
        if self.prevTime != self.theTime:
            cmds.undoInfo(undoName="moveSeveralKeys", openChunk=True)
            self.updatePosition()
            cmds.undoInfo(undoName="moveSeveralKeys", closeChunk=True)
        super(KeyFrameBtn, self).mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet("background-color: #FF99FF;")
        super(KeyFrameBtn, self).enterEvent(event)
        self.setFocus()

    def leaveEvent(self, event):
        if self.checked:
            self.setStyleSheet(self.redLightColor)
        else:
            self.setStyleSheet(self.redColor)

        super(KeyFrameBtn, self).leaveEvent(event)

    def select(self, addSel=False):
        if not addSel:
            for el in self.theTimeSlider.listKeys:
                el.checked = False
                el.setStyleSheet(self.redColor)
        self.checked = True
        cmds.evalDeferred(self.setFocus)
        self.setStyleSheet(self.redLightColor)

    def updatePosition(self, startPos=None, oneKeySize=None, start=None, end=None):
        if start == None or end == None:
            start = cmds.playbackOptions(q=True, minTime=True)
            end = cmds.playbackOptions(q=True, maxTime=True)

        isVisible = self.theTime >= start and self.theTime <= end

        # displayBand = True
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

    def __init__(self, theTime, theTimeSlider):
        super(KeyFrameBtn, self).__init__(None)
        self.checked = False

        self.setCursor(QtGui.QCursor(QtCore.Qt.SplitHCursor))
        if theTime == int(theTime):
            self.theTime = int(theTime)
        else:
            self.theTime = theTime

        self.theTimeSlider = theTimeSlider
        self.mainWindow = theTimeSlider.mainWindow

        self.setParent(self.theTimeSlider)
        self.resize(6, 40)
        self.setStyleSheet(self.redColor)

        cmds.evalDeferred(self.updatePosition)
        self.show()


class TheTimeSlider(QtGui.QWidget):
    def getSortedListKeysObj(self):
        return sorted(self.listKeys, key=lambda ky: ky.theTime)

    def addDisplayKey(self, theTime):
        keyFrameBtn = KeyFrameBtn(theTime, self)
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
