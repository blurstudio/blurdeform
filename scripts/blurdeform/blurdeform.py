# -*- coding: utf-8 -*
##
#   :namespace  blurdev.blurdeform
#
#   :remarks    GUI to work with the blurSculpt plugin
#
#   :author     [author::email]
#   :author     [author::company]
#   :date       03/22/17
#


# we import from blurdev.gui vs. QtGui becuase there are some additional management features for running the Dialog in multiple environments
from __future__ import print_function
from blurdev.gui import Dialog
from studio.gui.resource import Icons
from PyQt4 import QtGui, QtCore
import blurdev.debug
from . import extraWidgets, blurAddPose
from functools import partial

_icons = {
    "fromScene": Icons.getIcon("arrow-180"),
    "refresh": Icons.getIcon("arrow-circle-double"),
    "publish": Icons.getIcon("shotgun"),
    "Add": Icons.getIcon("plus-button"),
    "Delete": Icons.getIcon("cross-button"),
    "empty": Icons.getIcon("border-down"),
    "cancelEdit": Icons.getIcon(r"icons8\office\PNG\16\Editing\no_edit-16"),
    "edit": Icons.getIcon(r"icons8\office\PNG\16\Very_Basic\edit-16"),
}

import blurdev

from maya import cmds, mel
import sip


class BlurDeformDialog(Dialog):
    currentBlurNode = ""
    currentGeom = ""
    currentPose = ""

    # ---------------- All the Adds --------------------------------------------------------------
    def addDeformer(self):
        with extraWidgets.WaitCursorCtxt():
            newBlurSculpt = cmds.blurSculpt()
            self.currentBlurNode = newBlurSculpt
            geom = self.getGeom(self.currentBlurNode, transform=True)
            self.currentGeom = geom
            self.currentPose = ""
            self.refresh()

    def addNewPose(self, poseName, local=False, poseTransform=""):
        # geom, = cmds.listConnections (currentBlurNode, s=False, d=True, type = "mesh")
        dicCmd = {"poseName": poseName, "addPose": True}

        if local and poseTransform.strip() not in ["N/A", ""]:
            poseTransformExists = cmds.ls(poseTransform)
            if poseTransformExists:
                dicCmd["poseTransform"] = poseTransform

        cmds.blurSculpt(self.currentBlurNode, **dicCmd)

        poseList = cmds.getAttr(self.currentBlurNode + ".poses", mi=True)
        self.currentPose = "{0}.poses[{1}]".format(self.currentBlurNode, max(poseList))

        deformationType = 0 if local else 1  # maya type
        cmds.setAttr(self.currentPose + ".deformationType", deformationType)

        self.refreshListPoses(selectLast=True)
        # self.selectPose (poseName)

    def addNewFrame(self):
        cmds.selectMode(object=True)
        selection = cmds.ls(sl=True)
        if len(selection) != 1:
            cmds.confirmDialog(m="error select only one mesh")
            return

        # get the index
        if self.currentPose == "":
            res = cmds.confirmDialog(m="select a pose in the poses list  (left)")
            return

        listPoses = cmds.blurSculpt(self.currentBlurNode, query=True, listPoses=True)
        currTime = cmds.currentTime(q=True)
        dicVal = {"blurNode": self.currentBlurNode, "currentPose": self.currentPose}
        poseName = cmds.getAttr(self.currentPose + ".poseName")

        listDeformationsFrame = cmds.blurSculpt(
            self.currentBlurNode, query=True, listFrames=True, poseName=poseName
        )
        if not listDeformationsFrame:
            listDeformationsFrame = []
        listDeformationsIndices = cmds.getAttr(
            "{currentPose}.deformations".format(**dicVal), mi=True
        )

        if currTime in listDeformationsFrame:
            # empty it the channel
            frameIndex = listDeformationsIndices[listDeformationsFrame.index(currTime)]
            dicVal["indDeform"] = frameIndex

            indices = cmds.getAttr(
                "{currentPose}.deformations[{indDeform}].vectorMovements".format(
                    **dicVal
                ),
                mi=True,
            )
            if indices:
                for indVtx in indices:
                    dicVal["vtx"] = indVtx
                    cmds.removeMultiInstance(
                        "{currentPose}.deformations[{indDeform}].vectorMovements[{vtx}]".format(
                            **dicVal
                        ),
                        b=True,
                    )

        cmds.blurSculpt(self.currentGeom, addAtTime=selection[0], poseName=poseName)
        # theBasePanel = self.doIsolate (state=0)
        cmds.hide(selection[0])
        self.exitEditMode()

        self.refresh()

    def addEmptyFrame(self):
        poseName = cmds.getAttr(self.currentPose + ".poseName")
        listDeformationsIndices = map(
            int, cmds.getAttr(self.currentPose + ".deformations", mi=True)
        )
        dicVal = {"pose": self.currentPose}
        dicVal["frame"] = max(listDeformationsIndices) + 1

        currTime = cmds.currentTime(q=True)
        cmds.setAttr("{pose}.deformations[{frame}].frame".format(**dicVal), currTime)
        cmds.setAttr("{pose}.deformations[{frame}].gain".format(**dicVal), 1.0)

        self.refreshListFrames()

    def delete_frame(self):
        currentFrameItem = self.uiFramesTW.currentItem()
        if currentFrameItem:
            toDelete = str(currentFrameItem.data(0, QtCore.Qt.UserRole).toString())
            res = cmds.confirmDialog(
                title="delete",
                m="Do you want to delete the frame [{0}]?\nNo Undo".format(
                    currentFrameItem.text(0)
                ),
                b=("Yes", "No"),
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )
            if res == "Yes":
                cmds.removeMultiInstance(toDelete, b=True)
                self.refresh()

    def delete_pose(self):
        if cmds.objExists(self.currentPose):
            poseName = cmds.getAttr(self.currentPose + ".poseName")
            res = cmds.confirmDialog(
                title="delete",
                m="Do you want to delete the pose [{0}]?\nNo Undo".format(poseName),
                b=("Yes", "No"),
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )
            if res == "Yes":
                cmds.removeMultiInstance(self.currentPose, b=True)
                self.currentPose = ""
                self.refresh()

    def delete_sculpt(self):
        res = cmds.confirmDialog(
            title="delete",
            m="Do you want to delete the blurNode [{0}]?\nNo Undo".format(
                self.currentBlurNode
            ),
            b=("Yes", "No"),
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )
        if res == "Yes":
            cmds.delete(self.currentBlurNode)
            self.currentBlurNode = ""
            self.currentGeom = ""
            self.currentPose = ""
            self.refresh()

    # ----------------- ARRAY CHANGE FUNCTIONS -------------------------------
    def isValidName(self, theName, oldName=""):
        listPoses = cmds.blurSculpt(self.currentBlurNode, query=True, listPoses=True)
        if not listPoses:
            listPoses = []
        if listPoses and oldName:
            if oldName in listPoses:
                listPoses.remove(oldName)
        return theName not in listPoses

    def renamePose(self, item, column):
        newName = item.text(0)
        blurPose = str(item.data(0, QtCore.Qt.UserRole).toString())

        prevName = cmds.getAttr(blurPose + ".poseName")
        if newName != prevName:
            if self.isValidName(newName, oldName=prevName):
                cmds.setAttr(blurPose + ".poseName", newName, type="string")
            else:
                QtCore.QObject.disconnect(
                    self.uiPosesTW,
                    QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
                    self.renamePose,
                )
                item.setText(0, str(prevName))
                QtCore.QObject.connect(
                    self.uiPosesTW,
                    QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
                    self.renamePose,
                )

        # check state
        isChecked = item.checkState(column) == QtCore.Qt.Checked
        prevVal = cmds.getAttr(blurPose + ".poseEnabled")
        if isChecked != prevVal:
            cmds.setAttr(blurPose + ".poseEnabled", isChecked)

    def refreshPoseInfo(self, item, prevItem):
        blurPose = str(item.data(0, QtCore.Qt.UserRole).toString())
        self.currentPose = blurPose
        self.refreshListFrames()

        deformationType = cmds.getAttr(blurPose + ".deformationType")
        if deformationType == 0:
            inConnections = cmds.listConnections(
                blurPose + ".poseMatrix", s=True, d=False
            )
            if not inConnections:
                val = "N/A"
            else:
                val = inConnections[0]
            self.uiTransformLE.setText(val)
            self.uiLocalDeformationRB.setChecked(True)
        else:
            self.uiTangentDeformationRB.setChecked(True)
        self.uiTransformLE.setVisible(deformationType == 0)
        self.uiMatLBL.setVisible(deformationType == 0)
        self.uiPickTransformBTN.setVisible(deformationType == 0)

    def connectMatrix(self):
        selection = cmds.ls(sl=True, tr=True)
        if selection:
            self.uiTransformLE.setText(selection[0])
            cmds.connectAttr(
                selection[0] + ".matrix", self.currentPose + ".poseMatrix", f=True
            )

    def isValidFrame(self, newFrame, oldFrame=-1):
        poseName = str(cmds.getAttr(self.currentPose + ".poseName"))
        listDeformationsFrame = cmds.blurSculpt(
            self.currentBlurNode, query=True, listFrames=True, poseName=str(poseName)
        )
        if not listDeformationsFrame:
            listDeformationsFrame = []
        if listDeformationsFrame and oldFrame:
            if oldFrame in listDeformationsFrame:
                listDeformationsFrame.remove(oldFrame)
        return newFrame not in listDeformationsFrame

    def changeTheFrame(self, item, column):
        newFrame = item.text(0)
        try:
            floatFrame = float(newFrame)
        except ValueError:
            cmds.confirmDialog(m="not a float", title="ERROR")
            return
        frameChannel = str(item.data(0, QtCore.Qt.UserRole).toString())
        oldFrame = cmds.getAttr(frameChannel + ".frame")
        if floatFrame != oldFrame:
            if self.isValidFrame(floatFrame, oldFrame=oldFrame):
                cmds.setAttr(frameChannel + ".frame", floatFrame)
            else:
                QtCore.QObject.disconnect(
                    self.uiFramesTW,
                    QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
                    self.changeTheFrame,
                )
                item.setText(0, str(oldFrame))
                QtCore.QObject.connect(
                    self.uiFramesTW,
                    QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
                    self.changeTheFrame,
                )
        # check state

        isChecked = item.checkState(0) == QtCore.Qt.Checked
        prevVal = cmds.getAttr(frameChannel + ".frameEnabled")
        print("check", isChecked, prevVal)
        if isChecked != prevVal:
            cmds.setAttr(frameChannel + ".frameEnabled", isChecked)

    # ---------------------- display of ARRAY --------------------------------------

    def addKeyToTimePort(self, listDeformationsFrame):
        if self.addTimeLine:
            for keyTime in listDeformationsFrame:
                self.blurTimeSlider.addDisplayKey(keyTime, 0, "limegreen")

    def refreshListFrames(self):
        poseName = str(cmds.getAttr(self.currentPose + ".poseName"))
        QtCore.QObject.disconnect(
            self.uiFramesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.changeTheFrame,
        )

        self.uiFramesTW.clear()
        self.uiFramesTW.setColumnCount(4)
        self.uiFramesTW.setHeaderLabels(["frame", "\u00D8", "gain", "offset"])

        listDeformationsFrame = cmds.blurSculpt(
            self.currentBlurNode, query=True, listFrames=True, poseName=str(poseName)
        )

        if listDeformationsFrame:
            listDeformationsIndices = cmds.getAttr(
                self.currentPose + ".deformations", mi=True
            )
            if not listDeformationsIndices:
                listDeformationsIndices = []

            if listDeformationsFrame:
                self.addKeyToTimePort(listDeformationsFrame)

            listDeformationsFrameandIndices = [
                (listDeformationsFrame[i], listDeformationsIndices[i])
                for i in range(len(listDeformationsFrame))
            ]
            listDeformationsFrameandIndices.sort()
            for deformFrame, logicalFrameIndex in listDeformationsFrameandIndices:
                frameItem = QtGui.QTreeWidgetItem()
                frameItem.setText(0, str(deformFrame))
                frameItem.setFlags(
                    frameItem.flags()
                    | QtCore.Qt.ItemIsEditable
                    | QtCore.Qt.ItemIsUserCheckable
                )

                checkState = cmds.getAttr(
                    self.currentPose
                    + ".deformations[{0}].frameEnabled".format(logicalFrameIndex)
                )
                if checkState:
                    frameItem.setCheckState(0, QtCore.Qt.Checked)
                else:
                    frameItem.setCheckState(0, QtCore.Qt.Unchecked)

                frameItem.setData(
                    0,
                    QtCore.Qt.UserRole,
                    self.currentPose + ".deformations[{0}]".format(logicalFrameIndex),
                )
                frameItem.setText(2, "0.")
                frameItem.setText(3, "0.")

                vectorMovementsIndices = cmds.getAttr(
                    self.currentPose
                    + ".deformations[{0}].vectorMovements".format(logicalFrameIndex),
                    mi=True,
                )
                if not vectorMovementsIndices:
                    frameItem.setBackground(0, QtGui.QBrush(self.blueCol))
                    frameItem.setText(1, "\u00D8")
                    frameItem.setTextAlignment(1, QtCore.Qt.AlignCenter)

                self.uiFramesTW.addTopLevelItem(frameItem)
                newWidgetGain = extraWidgets.spinnerWidget(
                    self.currentPose
                    + ".deformations[{0}].gain".format(logicalFrameIndex),
                    singleStep=0.1,
                    precision=2,
                )
                newWidgetGain.setMinimumHeight(20)
                newWidgetOffset = extraWidgets.spinnerWidget(
                    self.currentPose
                    + ".deformations[{0}].offset".format(logicalFrameIndex),
                    singleStep=0.1,
                    precision=2,
                )
                self.uiFramesTW.setItemWidget(frameItem, 2, newWidgetGain)
                self.uiFramesTW.setItemWidget(frameItem, 3, newWidgetOffset)

        vh = self.uiFramesTW.header()
        vh.setStretchLastSection(False)
        vh.setResizeMode(QtGui.QHeaderView.Stretch)
        vh.setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.uiFramesTW.setColumnWidth(1, 20)
        vh.setResizeMode(1, QtGui.QHeaderView.Fixed)
        self.uiFramesTW.setColumnWidth(2, 50)
        vh.setResizeMode(2, QtGui.QHeaderView.Fixed)
        self.uiFramesTW.setColumnWidth(3, 50)
        vh.setResizeMode(3, QtGui.QHeaderView.Fixed)
        cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 1, 20))
        cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 2, 50))
        cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 3, 50))

        QtCore.QObject.connect(
            self.uiFramesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.changeTheFrame,
        )

    #        vv.setResizeMode(QtGui.QHeaderView.Stretch)

    def refreshListPoses(self, selectLast=False):
        QtCore.QObject.disconnect(
            self.uiPosesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.renamePose,
        )
        QtCore.QObject.disconnect(
            self.uiPosesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.refreshPoseInfo,
        )

        self.currentPose = ""
        self.uiPosesTW.clear()
        self.uiFramesTW.clear()

        self.uiPosesTW.setColumnCount(3)
        self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])

        listPoses = cmds.blurSculpt(self.currentBlurNode, query=True, listPoses=True)
        if not listPoses:
            return
        # print "list Poses is " + listPoses
        dicVal = {"blurNode": self.currentBlurNode}

        posesIndices = map(int, cmds.getAttr(self.currentBlurNode + ".poses", mi=True))
        for indNm, thePose in enumerate(listPoses):
            logicalInd = posesIndices[indNm]
            channelItem = QtGui.QTreeWidgetItem()
            channelItem.setText(0, thePose)
            channelItem.setText(1, "0.")
            channelItem.setText(2, "0.")

            channelItem.setFlags(
                channelItem.flags()
                | QtCore.Qt.ItemIsUserCheckable
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEditable
            )

            # store the logical index
            dicVal["indPose"] = logicalInd
            checkState = cmds.getAttr(
                "{blurNode}.poses[{indPose}].poseEnabled".format(**dicVal)
            )
            if checkState:
                channelItem.setCheckState(0, QtCore.Qt.Checked)
            else:
                channelItem.setCheckState(0, QtCore.Qt.Unchecked)

            self.uiPosesTW.addTopLevelItem(channelItem)
            # store for delation
            channelItem.setData(
                0, QtCore.Qt.UserRole, "{blurNode}.poses[{indPose}]".format(**dicVal)
            )

            newWidgetGain = extraWidgets.spinnerWidget(
                "{blurNode}.poses[{indPose}].poseGain".format(**dicVal),
                singleStep=0.1,
                precision=2,
            )
            newWidgetGain.setMinimumHeight(20)
            newWidgetOffset = extraWidgets.spinnerWidget(
                "{blurNode}.poses[{indPose}].poseOffset".format(**dicVal),
                singleStep=0.1,
                precision=2,
            )
            self.uiPosesTW.setItemWidget(channelItem, 1, newWidgetGain)
            self.uiPosesTW.setItemWidget(channelItem, 2, newWidgetOffset)

        vh = self.uiPosesTW.header()
        vh.setStretchLastSection(False)
        vh.setResizeMode(QtGui.QHeaderView.Stretch)
        vh.setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.uiPosesTW.setColumnWidth(1, 50)
        vh.setResizeMode(1, QtGui.QHeaderView.Fixed)
        self.uiPosesTW.setColumnWidth(2, 50)
        vh.setResizeMode(2, QtGui.QHeaderView.Fixed)
        cmds.evalDeferred(partial(self.uiPosesTW.setColumnWidth, 1, 50))
        cmds.evalDeferred(partial(self.uiPosesTW.setColumnWidth, 2, 50))

        QtCore.QObject.connect(
            self.uiPosesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.refreshPoseInfo,
        )
        QtCore.QObject.connect(
            self.uiPosesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.renamePose,
        )

        if len(listPoses) > 0:
            if selectLast:
                self.uiPosesTW.setCurrentItem(channelItem)
            else:
                self.uiPosesTW.setCurrentItem(self.uiPosesTW.topLevelItem(0))

    def changedSelection(self, item, preItem):
        # blurdev.debug.debugMsg( "hello "  +  item.row (), blurdev.debug.DebugLevel.High)
        self.currentBlurNode = str(item.text(0))
        self.currentGeom = str(item.text(1))
        self.refreshListPoses()

    def fillTreeOfBlurNodes(self):
        QtCore.QObject.disconnect(
            self.uiBlurNodesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.changedSelection,
        )

        self.uiBlurNodesTW.clear()
        self.uiBlurNodesTW.setColumnCount(2)
        self.uiBlurNodesTW.setHeaderLabels(["blurSculpt", "mesh"])
        self.uiBlurNodesTW.setExpandsOnDoubleClick(False)

        blurNodes = cmds.ls(type="blurSculpt")
        for blrNode in blurNodes:
            geom = self.getGeom(blrNode, transform=True)
            channelItem = QtGui.QTreeWidgetItem()
            channelItem.setText(0, blrNode)
            channelItem.setText(1, geom)
            self.uiBlurNodesTW.addTopLevelItem(channelItem)

        itemsHeight = 38 + len(blurNodes) * 17
        minH = 50 if itemsHeight < 50 else itemsHeight
        maxH = 150 if itemsHeight > 150 else itemsHeight
        self.uiBlurNodesTW.setMinimumHeight(minH)
        self.uiListDeformersGB.setMaximumHeight(maxH)

        QtCore.QObject.connect(
            self.uiBlurNodesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.changedSelection,
        )
        for i in range(2):
            self.uiBlurNodesTW.resizeColumnToContents(i)

    def doubleClickChannel(self, item, column):
        toSelect = str(item.text(column))
        if cmds.objExists(toSelect):
            cmds.select(toSelect)

    def getGeom(self, currentBlurNode, transform=False):
        futureHistory = cmds.listHistory(currentBlurNode, f=True, af=True)
        if futureHistory:
            meshHist = cmds.ls(futureHistory, type="mesh")
            if transform:
                (prt,) = cmds.listRelatives(meshHist, path=True, p=True)
                return prt
            return meshHist[0]
        return ""

    def selectFromScene(self):
        currentSel = cmds.ls(sl=True)
        if len(currentSel) == 1:
            obj = currentSel
            hist = cmds.listHistory(obj)
            if hist:
                blurSculpts = cmds.ls(hist, type="blurSculpt")

            if hist and blurSculpts:
                blurNodes = cmds.ls(type="blurSculpt")
                ind = blurNodes.index(blurSculpts[0])
                item = self.uiBlurNodesTW.topLevelItem(ind)
                self.uiBlurNodesTW.setCurrentItem(item)
                # index = self.uiBlurNodesTW.model().index(ind, 0)
                # self.uiBlurNodesTW.selectionModel().setCurrentIndex (index, QtGui.QItemSelectionModel.selectedRows)
            else:
                ind = -1

    # ----------------------- EDIT MODE  --------------------------------------------------
    def enterEditMode(self):
        (self.resForDuplicate,) = cmds.duplicate(self.currentGeom, name="TMPEDIT")
        cmds.select(self.currentGeom)
        cmds.HideSelectedObjects()
        cmds.select(self.resForDuplicate)
        cmds.selectMode(component=True)

    def exitEditMode(self):
        if cmds.objExists(self.resForDuplicate):
            cmds.delete(self.resForDuplicate)
            self.resForDuplicate = ""
        cmds.showHidden(self.currentGeom, a=True)
        cmds.selectMode(object=True)

    # ------------------- REFRESH ----------------------------------------------------

    def refresh(self):
        QtCore.QObject.disconnect(
            self.uiBlurNodesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.changedSelection,
        )
        QtCore.QObject.disconnect(
            self.uiPosesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.renamePose,
        )
        QtCore.QObject.disconnect(
            self.uiFramesTW,
            QtCore.SIGNAL("itemChanged(QTreeWidgetItem*,int)"),
            self.changeTheFrame,
        )
        QtCore.QObject.disconnect(
            self.uiPosesTW,
            QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)"),
            self.refreshPoseInfo,
        )

        self.uiPosesTW.clear()
        self.uiFramesTW.clear()

        # self.currentBlurNode = ""
        # self.currentGeom = ""
        currentPose = self.currentPose

        self.uiPosesTW.setColumnCount(3)
        self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])
        self.uiFramesTW.setColumnCount(4)
        self.uiFramesTW.setHeaderLabels(["frame", "\u00D8", "gain", "offset"])

        self.fillTreeOfBlurNodes()

        blurNodes = cmds.ls(type="blurSculpt")

        if self.currentBlurNode in blurNodes:
            ind = blurNodes.index(self.currentBlurNode)
            item = self.uiBlurNodesTW.topLevelItem(ind)
            self.uiBlurNodesTW.setCurrentItem(item)

            foundPose = False
            for i in range(self.uiPosesTW.topLevelItemCount()):
                itemPose = self.uiPosesTW.topLevelItem(i)
                thePose = str(itemPose.data(0, QtCore.Qt.UserRole).toString())
                if thePose == currentPose:
                    foundPose = True
                    self.uiPosesTW.setCurrentItem(itemPose)
                    break
            print("foundPose " + str(foundPose))
            if not foundPose:
                self.currentPose = ""

        else:
            self.currentBlurNode = ""
            self.currentGeom = ""
            self.currentPose = ""

    def resizePoseInfo(self, checkState):
        if checkState:
            self.uiPoseGB.setMaximumHeight(1000)
        else:
            self.uiPoseGB.setMaximumHeight(20)

    # ------------------- POPUP ----------------------------------------------------
    def create_popup_menu(self, parent=None):
        self.popup_menu = QtGui.QMenu(parent)
        self.popup_menu.addAction("jumpToFrame", self.jumpToFrame)
        self.popup_menu.addAction("select influenced vertices", self.selectVertices)
        self.popup_menu.addAction("delete", self.delete_frame)

    def on_context_menu(self, event):
        pos = event.pos()
        self.clickedItem = self.uiFramesTW.itemAt(pos)
        self.popup_menu.exec_(event.globalPos())

    def jumpToFrame(self):
        frameIndex = float(self.clickedItem.text(0))
        cmds.currentTime(frameIndex)

    def selectVertices(self):
        frameChannel = str(self.clickedItem.data(0, QtCore.Qt.UserRole).toString())
        vertices = cmds.getAttr(frameChannel + ".vectorMovements", mi=True)
        if vertices:
            toSelect = [
                "{0}.vtx[{1}]".format(self.currentGeom, vtx) for vtx in vertices
            ]
            cmds.select(toSelect)
        else:
            cmds.select(clear=True)

    # ------------------- EXTERNAL CALL ----------------------------------------------------
    def callAddPose(self):
        self.toRestore = []
        for el in self.__dict__.values():
            try:
                if self.isEnabled():
                    el.setEnabled(False)
                    self.toRestore.append(el)
            except:
                continue
        blurdev.launch(blurAddPose.BlurAddPose, instance=True)
        self.addPoseWin.refreshWindow()

        """
        addPoseWindow = blurAddPose.BlurAddPose ( parentWin = self)
        addPoseWindow.show ()
        """

    addPoseWin = None
    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(BlurDeformDialog, self).__init__(parent)
        # load the ui
        import __main__

        __main__.__dict__["blurDeformWindow"] = self

        blurdev.gui.loadUi(__file__, self)

        for nameBtn in ["PoseBTN", "FrameBTN", "BlurNodeBTN"]:
            for nm in ["Add", "Delete"]:
                btn = self.__dict__["ui{0}{1}".format(nm, nameBtn)]
                btn.setIcon(_icons[nm])
                btn.setText("")

        for nm in ["BlurNodes", "Frames", "Poses"]:
            self.__dict__["ui" + nm + "TW"].setRootIsDecorated(False)

        self.blueCol = QtGui.QColor(50, 50, 100)

        self.uiRefreshBTN.setIcon(_icons["refresh"])
        self.uiRefreshBTN.setText("")
        self.uiFromSelectionBTN.setIcon(_icons["fromScene"])
        self.uiFromSelectionBTN.setText("")
        self.uiEmptyFrameBTN.setIcon(_icons["empty"])
        self.uiEmptyFrameBTN.setText("")

        self.uiEditModeBTN.setIcon(_icons["edit"])
        self.uiExitEditModeBTN.setIcon(_icons["cancelEdit"])

        self.create_popup_menu()
        self.uiFramesTW.contextMenuEvent = self.on_context_menu

        QtCore.QObject.connect(
            self.uiPoseGB, QtCore.SIGNAL("toggled(bool)"), self.resizePoseInfo
        )
        QtCore.QObject.connect(
            self.uiRefreshBTN, QtCore.SIGNAL("clicked()"), self.refresh
        )
        QtCore.QObject.connect(
            self.uiFromSelectionBTN, QtCore.SIGNAL("clicked()"), self.selectFromScene
        )
        QtCore.QObject.connect(
            self.uiEmptyFrameBTN, QtCore.SIGNAL("clicked()"), self.addEmptyFrame
        )

        # - delete
        QtCore.QObject.connect(
            self.uiDeleteBlurNodeBTN, QtCore.SIGNAL("clicked()"), self.delete_sculpt
        )
        QtCore.QObject.connect(
            self.uiDeleteFrameBTN, QtCore.SIGNAL("clicked()"), self.delete_frame
        )
        QtCore.QObject.connect(
            self.uiDeletePoseBTN, QtCore.SIGNAL("clicked()"), self.delete_pose
        )
        # - Add
        QtCore.QObject.connect(
            self.uiAddBlurNodeBTN, QtCore.SIGNAL("clicked()"), self.addDeformer
        )
        QtCore.QObject.connect(
            self.uiAddFrameBTN, QtCore.SIGNAL("clicked()"), self.addNewFrame
        )
        QtCore.QObject.connect(
            self.uiAddPoseBTN, QtCore.SIGNAL("clicked()"), self.callAddPose
        )
        QtCore.QObject.connect(
            self.uiEditModeBTN, QtCore.SIGNAL("clicked()"), self.enterEditMode
        )
        QtCore.QObject.connect(
            self.uiExitEditModeBTN, QtCore.SIGNAL("clicked()"), self.exitEditMode
        )

        QtCore.QObject.connect(
            self.uiPickTransformBTN, QtCore.SIGNAL("clicked()"), self.connectMatrix
        )

        QtCore.QObject.connect(
            self.uiBlurNodesTW,
            QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem*,int)"),
            self.doubleClickChannel,
        )

        self.addTimeLine = False
        # time slider part
        if self.addTimeLine:
            self.blurTimeSlider = extraWidgets.TheTimeSlider(self)
            self.layout().addWidget(self.blurTimeSlider)
        # cmds.evalDeferred (self.refreshForShow )
        self.uiPoseGB.setChecked(False)

    def addtheCallBack(self):
        print("ADD Call Back")
        self.playBackScript = cmds.scriptJob(
            e=["playbackRangeChanged", self.blurTimeSlider.updateKeys], protected=True
        )
        # scriptJob( kill=jobNum, force=True)

    def deleteScriptJob(self):
        print("Delete Call Back")
        cmds.scriptJob(kill=self.playBackScript, force=True)

    def refreshForShow(self):
        print("CALLING REFRESH OPENING")
        if self.addTimeLine:
            self.addtheCallBack()

        self.currentBlurNode = ""
        self.currentGeom = ""
        self.currentPose = ""
        self.resForDuplicate = ""

        cmds.evalDeferred(self.refresh)

    def showEvent(self, event):
        self.refreshForShow()
        super(BlurDeformDialog, self).showEvent(event)

    def closeEvent(self, event):
        if self.addTimeLine:
            self.deleteScriptJob()
        super(BlurDeformDialog, self).closeEvent(event)


"""
        validNickname = QtCore.QRegExp ("^[0-9]*$")        
        validator = QtGui.QRegExpValidator (validNickname ,self.main_ui.resolution_le)

"""
