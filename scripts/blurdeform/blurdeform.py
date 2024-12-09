# -*- coding: utf-8 -*
##
#   :namespace  blurdeform.blurdeform
#
#   :remarks    GUI to work with the blurSculpt plugin
#
#   :author     [author::guillaume@blur.com]
#   :author     [author::blur]
#   :date       03/22/17
#

from __future__ import print_function
from __future__ import absolute_import

import os
import codecs

from functools import partial
from xml.dom import minidom
from xml.etree import ElementTree
from maya import cmds, mel, OpenMaya

from .Qt import QtGui, QtCore, QtWidgets, QtCompat
from . import extraWidgets, blurAddPose, blurDeformQueryMeshes, storeXml, utils

import six
from six.moves import range, map, zip

try:
    # Blur adds some extra signal handling to the top-level dialogs
    from blurdev.gui import Dialog
except ImportError:
    Dialog = QtWidgets.QDialog


def orderMelList(listInd, onlyStr=True):
    listIndString = []
    listIndStringAndCount = []

    it = iter(listInd)
    currentValue = next(it)
    while True:
        try:
            firstVal = currentValue
            theVal = firstVal
            while currentValue == theVal:
                currentValue = next(it)
                theVal += 1
            theVal -= 1
            if firstVal != theVal:
                theStr = "{0}:{1}".format(firstVal, theVal)
            else:
                theStr = str(firstVal)
            listIndString.append(theStr)
            listIndStringAndCount.append((theStr, theVal - firstVal + 1))

        except StopIteration:
            if firstVal != theVal:
                theStr = "{0}:{1}".format(firstVal, theVal)
            else:
                theStr = str(firstVal)
            listIndString.append(theStr)
            listIndStringAndCount.append((theStr, theVal - firstVal + 1))
            break
    if onlyStr:
        return listIndString
    else:
        return listIndStringAndCount


def getVertsSelection():
    richSelList = OpenMaya.MSelectionList()
    OpenMaya.MGlobal.getActiveSelectionList(richSelList)

    toReturn = {}
    if richSelList.isEmpty():
        return toReturn

    iterSel = OpenMaya.MItSelectionList(richSelList)

    while not iterSel.isDone():
        component = OpenMaya.MObject()
        dagPath = OpenMaya.MDagPath()
        try:
            iterSel.getDagPath(dagPath, component)
        except Exception:
            iterSel.next()
            continue
        transform = dagPath.transform()
        depNode = OpenMaya.MFnDependencyNode(transform)
        depNode_name = cmds.ls(depNode.uniqueName())[0]

        if component.isNull():
            iterSel.next()
            continue

        elementIndices = []
        componentFn = OpenMaya.MFnComponent(component)
        count = componentFn.elementCount()
        if componentFn.componentType() == OpenMaya.MFn.kMeshPolygonComponent:
            polyIter = OpenMaya.MItMeshPolygon(dagPath, component)
            setOfVerts = set()
            connectedVertices = OpenMaya.MIntArray()
            while not polyIter.isDone():
                polyIter.getVertices(connectedVertices)
                setOfVerts.update(list(connectedVertices))
                polyIter.next()
            elementIndices.extend(list(setOfVerts))

        elif componentFn.componentType() == OpenMaya.MFn.kMeshEdgeComponent:
            edgeIter = OpenMaya.MItMeshEdge(dagPath, component)
            setOfVerts = set()
            while not edgeIter.isDone():
                setOfVerts.add(edgeIter.index(0))
                setOfVerts.add(edgeIter.index(1))
                edgeIter.next()
            elementIndices.extend(list(setOfVerts))

        elif componentFn.componentType() == OpenMaya.MFn.kMeshVertComponent:
            singleFn = OpenMaya.MFnSingleIndexedComponent(component)
            for i in range(count):
                elementIndices.append(singleFn.element(i))

        toReturn[depNode_name] = sorted(elementIndices)
        iterSel.next()
    return toReturn


class BlurDeformDialog(Dialog):
    def deltasCopy(self):
        selectedFrames = self.uiFramesTW.selectedItems()
        if not selectedFrames:
            return
        frameItem = selectedFrames[0]
        frameName = str(frameItem.data(0, QtCore.Qt.UserRole))
        self.copiedFrame = frameName

    def deltasPaste(self):
        selectedFrames = self.uiFramesTW.selectedItems()
        if not selectedFrames:
            return

        isMultiGeos = len(self.currentGeometries) > 1
        indicesToCopy = []
        if isMultiGeos:
            self.blurDeformQueryMeshesWin = utils.launchDialog(
                self,
                blurDeformQueryMeshes.BlurDeformQueryMeshes,
                self.blurDeformQueryMeshesWin,
                modal=True,
                instanced=True,
                lstMeshes=self.currentGeometries,
                listToSelect=self.currentGeometries,
                addComboMeshes=None

            )
            # self.blurDeformQueryMeshesWin.refreshWindow(
            #     self.currentGeometries, self.currentGeometries, None
            # )

            selectedMeshes = self.blurDeformQueryMeshesWin.listSelectedMeshes
            indicesMeshes = list(
                zip(self.currentGeometriesIndices, self.currentGeometries)
            )
            for index, geo in indicesMeshes:
                if geo in selectedMeshes:
                    indicesToCopy.append(index)
        else:
            indicesToCopy = self.currentGeometriesIndices

        if not indicesToCopy:
            return

        # First COPY ------------------------
        dicOfCOPYvalues = {}
        copiedFrameIndices = (
            cmds.getAttr(self.copiedFrame + ".storedVectors", mi=True) or []
        )
        for indexGeo in copiedFrameIndices:
            indicesVectorMvt = cmds.getAttr(
                self.copiedFrame
                + ".storedVectors[{}].multiVectorMovements".format(indexGeo),
                mi=True,
            )
            if indicesVectorMvt:
                vectorMvts = []
                for indexVtx in indicesVectorMvt:
                    (val,) = cmds.getAttr(
                        self.copiedFrame
                        + ".storedVectors[{}].multiVectorMovements[{}]".format(
                            indexGeo, indexVtx
                        )
                    )
                    vectorMvts.append((indexVtx, val))
                dicOfCOPYvalues[indexGeo] = vectorMvts

        # Now PASTE ----------------------
        # first we clear all mvts
        for frameItem in selectedFrames:
            frameName = str(frameItem.data(0, QtCore.Qt.UserRole))
            storedVectorsIndices = (
                cmds.getAttr(frameName + ".storedVectors", mi=True) or []
            )
            for indexGeo in indicesToCopy:  # remove if it's in the copy list
                if indexGeo in storedVectorsIndices:
                    cmds.removeMultiInstance(
                        frameName + ".storedVectors[{}]".format(indexGeo),
                        b=True,
                    )

            # then set them
            for indexGeo in indicesToCopy:  # remove if it's in the copy list
                if indexGeo in dicOfCOPYvalues:
                    vectorMvts = dicOfCOPYvalues[indexGeo]
                    for indexVtx, val in vectorMvts:
                        cmds.setAttr(
                            frameName
                            + ".storedVectors[{}].multiVectorMovements[{}]".format(
                                indexGeo, indexVtx
                            ),
                            *val
                        )

    def bake(self, typeOfBake=""):
        # self.applyScriptJob=False
        tim = cmds.currentTime(q=True)
        with extraWidgets.WaitCursorCtxt(suspendRefresh=True):
            selectedFrames = self.uiFramesTW.selectedItems()

            for frameItem in selectedFrames:
                frameName = str(frameItem.data(0, QtCore.Qt.UserRole))
                geoIndices = cmds.getAttr(frameName + ".storedVectors", mi=True) or []
                dicVal = {"frameName": frameName, "typeOfBake": typeOfBake}
                attributeForBaking = "{frameName}.{typeOfBake}".format(**dicVal)
                for geoIndex in geoIndices:
                    dicVal["geoIndex"] = geoIndex

                    # getAttr at time doesn't always work because maya is horrible
                    frame = cmds.getAttr("{frameName}.frame".format(**dicVal))
                    cmds.currentTime(frame)
                    percent = cmds.getAttr(attributeForBaking)
                    if typeOfBake == "offset":
                        percent += 1.0

                    vectorMovementsIndices = (
                        cmds.getAttr(
                            "{frameName}.storedVectors[{geoIndex}].multiVectorMovements".format(
                                **dicVal
                            ),
                            mi=True,
                        )
                        or []
                    )
                    for vertexInd in vectorMovementsIndices:
                        dicVal["vertexIndex"] = vertexInd
                        vtxStorage = "{frameName}.storedVectors[{geoIndex}].multiVectorMovements[{vertexIndex}]".format(
                            **dicVal
                        )
                        (val,) = cmds.getAttr(vtxStorage)
                        newValue = [vec * percent for vec in val]
                        cmds.setAttr(vtxStorage, *newValue)
                # here
                inConn = cmds.listConnections(
                    attributeForBaking, s=True, d=False, p=True
                )
                if inConn:
                    cmds.disconnectAttr(inConn[0], attributeForBaking)
                valReset = 0.0 if typeOfBake == "offset" else 1.0
                cmds.setAttr(attributeForBaking, valReset)
        cmds.currentTime(tim)

    def setSelectedVerticestoInBetweenFrame(self):
        selectedVertices = getVertsSelection()
        if not selectedVertices:
            return
        selectedFrames = self.uiFramesTW.selectedItems()
        if not selectedFrames:
            return

        # work only for 1 frame at a time right now
        frameItem = selectedFrames[0]
        frameName = str(frameItem.data(0, QtCore.Qt.UserRole))

        frameIndex = cmds.getAttr(frameName + ".frame")
        cmds.currentTime(frameIndex)

        # 0 storeBasicMvt
        currentPosi = {}
        for geo, vertices in six.iteritems(selectedVertices):
            toGetPosi = ["{}.vtx[{}]".format(geo, el) for el in orderMelList(vertices)]
            xDest = cmds.xform(toGetPosi, q=True, ws=True, t=True)
            currentPosi[geo] = xDest

        # 1 - disable frame
        cmds.setAttr(frameName + ".frameEnabled", 0)

        # 2 - store position
        theDeltas = {}
        for geo, vertices in six.iteritems(selectedVertices):
            toGetPosi = ["{}.vtx[{}]".format(geo, el) for el in orderMelList(vertices)]
            xDest = cmds.xform(toGetPosi, q=True, ws=True, t=True)
            deltas = [a_i - b_i for a_i, b_i in zip(xDest, currentPosi[geo])]
            theDeltas[geo] = list(zip(deltas[0::3], deltas[1::3], deltas[2::3]))

        # 3 - enable frame
        cmds.setAttr(frameName + ".frameEnabled", 1)

        # 4 - now apply
        storedVectorsIndices = cmds.getAttr(frameName + ".storedVectors", mi=True) or []

        for geo, thevertIndices in six.iteritems(selectedVertices):
            if geo in self.currentGeometries:
                indexGeo = self.currentGeometriesIndices[
                    self.currentGeometries.index(geo)
                ]
                if indexGeo in storedVectorsIndices:
                    mvtIndices = (
                        cmds.getAttr(
                            frameName
                            + ".storedVectors[{}].multiVectorMovements".format(
                                indexGeo
                            ),
                            mi=True,
                        )
                        or []
                    )
                else:
                    mvtIndices = []
                for i, indexVtx in enumerate(thevertIndices):
                    deltaMvt = theDeltas[geo][i]
                    if indexVtx in mvtIndices:
                        (currentVal,) = cmds.getAttr(
                            frameName
                            + ".storedVectors[{}].multiVectorMovements[{}]".format(
                                indexGeo, indexVtx
                            )
                        )
                        addMVt = [deltaMvt[i] + currentVal[i] for i in range(3)]
                        cmds.setAttr(
                            frameName
                            + ".storedVectors[{}].multiVectorMovements[{}]".format(
                                indexGeo, indexVtx
                            ),
                            *addMVt
                        )
                    else:
                        cmds.setAttr(
                            frameName
                            + ".storedVectors[{}].multiVectorMovements[{}]".format(
                                indexGeo, indexVtx
                            ),
                            *deltaMvt
                        )

    def removeSelectedVerticesFromFrame(self):
        selectedVertices = getVertsSelection()
        if not selectedVertices:
            cmds.confirmDialog(t="remove verts", m="select some vertices\nFailed")
            return
        # get an easy array to deal with
        indicesMeshes = sorted(
            zip(self.currentGeometriesIndices, self.currentGeometries)
        )
        lstMsh = [""] * (max(self.currentGeometriesIndices) + 1)
        for ind, msh in indicesMeshes:
            lstMsh[ind] = msh

        selectedFrames = self.uiFramesTW.selectedItems()
        if not selectedFrames:
            return

        for frameItem in selectedFrames:
            frameName = str(frameItem.data(0, QtCore.Qt.UserRole))

            storedVectorsIndices = (
                cmds.getAttr(frameName + ".storedVectors", mi=True) or []
            )
            for indexGeo in storedVectorsIndices:
                geoName = lstMsh[indexGeo]
                if geoName not in selectedVertices:
                    continue
                verticesIndToDelete = selectedVertices[geoName]

                mvtIndices = cmds.getAttr(
                    frameName
                    + ".storedVectors[{}].multiVectorMovements".format(indexGeo),
                    mi=True,
                )
                if mvtIndices:
                    mvtIndices = list(map(int, mvtIndices))
                    toDeleteSet = set(verticesIndToDelete).intersection(set(mvtIndices))
                    if len(toDeleteSet) == len(mvtIndices):  # delete All the array
                        cmds.removeMultiInstance(
                            frameName + ".storedVectors[{}]".format(indexGeo),
                            b=True,
                        )
                    else:
                        for indVtx in toDeleteSet:
                            cmds.removeMultiInstance(
                                frameName
                                + ".storedVectors[{}].multiVectorMovements[{}]".format(
                                    indexGeo, indVtx
                                ),
                                b=True,
                            )

    def getListDeformationFrames(self):
        defIndices = cmds.getAttr(self.currentPose + ".deformations", mi=True)
        if not defIndices:
            defIndices = []
        listDeformationsIndices = list(map(int, defIndices))
        listDeformationsFrame = [
            cmds.getAttr(self.currentPose + ".deformations[{0}].frame".format(ind))
            for ind in listDeformationsIndices
        ]

        return listDeformationsFrame

    # ---------------- All the Adds --------------------------------------------------------------
    def addDeformer(self):
        with extraWidgets.WaitCursorCtxt():
            newBlurSculpt = cmds.deformer(type="blurSculpt")

            (self.currentBlurNode,) = newBlurSculpt
            (
                self.currentGeometries,
                self.currentGeometriesIndices,
            ) = self.getGeom(self.currentBlurNode, transform=True)

            self.currentPose = ""
            self.refresh()

    def addMeshToDeformer(self):
        sel = cmds.ls(sl=True, tr=True)
        cmds.deformer(self.currentBlurNode, e=True, g=sel)
        self.refresh()

    def addNewPose(self, poseName, local=False, poseTransform="", withRefresh=True):
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

        if withRefresh:
            self.refreshListPoses(selectLast=True)

    def doDuplicate(self):
        frameIndex = float(self.clickedItem.text(0))
        result = cmds.promptDialog(
            title="Duplicate Frame",
            message="Enter new Frame:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if result == "OK":
            text = cmds.promptDialog(query=True, text=True)
            try:
                newTime = float(text)
            except Exception:
                return
            self.duplicateFrame(frameIndex, newTime)

    def duplicateFrame(self, prevTime, currTime):
        with extraWidgets.WaitCursorCtxt():
            listDeformationsIndices = list(
                map(
                    int,
                    cmds.getAttr(self.currentPose + ".deformations", mi=True),
                )
            )

            dicVal = {"pose": self.currentPose}

            listDeformationsFrame = {}
            for ind in listDeformationsIndices:
                dicVal["ind"] = ind
                frame = cmds.getAttr(
                    "{pose}.deformations[{ind}].frame".format(**dicVal)
                )
                listDeformationsFrame[frame] = ind

            if prevTime not in listDeformationsFrame:
                return
            oldIndex = listDeformationsFrame[prevTime]

            dicVal["frame"] = max(listDeformationsIndices) + 1
            dicVal["prevFrame"] = oldIndex

            for att in ["gain", "offset", "frameEnabled"]:
                val = cmds.getAttr(
                    "{pose}.deformations[{prevFrame}].".format(**dicVal) + att
                )
                cmds.setAttr(
                    "{pose}.deformations[{frame}].".format(**dicVal) + att, val
                )
            cmds.setAttr(
                "{pose}.deformations[{frame}].frame".format(**dicVal), currTime
            )

            storedVectorsIndices = (
                cmds.getAttr(
                    "{pose}.deformations[{prevFrame}].storedVectors".format(**dicVal),
                    mi=True,
                )
                or []
            )
            for indexGeo in storedVectorsIndices:
                dicVal["indexGeo"] = indexGeo
                indicesVectorMvt = cmds.getAttr(
                    "{pose}.deformations[{prevFrame}].storedVectors[{indexGeo}].multiVectorMovements".format(
                        **dicVal
                    ),
                    mi=True,
                )
                if indicesVectorMvt:
                    for ind in indicesVectorMvt:
                        dicVal["vecInd"] = ind
                        (val,) = cmds.getAttr(
                            "{pose}.deformations[{prevFrame}].storedVectors[{indexGeo}].multiVectorMovements[{vecInd}]".format(
                                **dicVal
                            )
                        )
                        cmds.setAttr(
                            "{pose}.deformations[{frame}].storedVectors[{indexGeo}].multiVectorMovements[{vecInd}]".format(
                                **dicVal
                            ),
                            *val
                        )

        QtCore.QTimer.singleShot(
            0, partial(self.refresh, selectTime=True, selTime=currTime)
        )

    def addNewFrame(self):
        if self.currentPose == "":
            return

        isMultiGeos = len(self.currentGeometries) > 1

        cmds.selectMode(object=True)
        selection = cmds.ls(sl=True, tr=True)
        toHide = []
        objsToAdd = []
        if not selection:
            objsToAdd = self.resForDuplicate
        else:
            objsWithAttributes = [
                geo
                for geo in selection
                if cmds.attributeQuery("blurSculptIndex", node=geo, ex=True)
            ]
            if objsWithAttributes:
                listResForDuplicate = cmds.ls(self.resForDuplicate)
                listResForDuplicate.extend(
                    set(objsWithAttributes) - set(listResForDuplicate)
                )
                if len(listResForDuplicate) != len(objsWithAttributes):
                    self.blurDeformQueryMeshesWin = utils.launchDialog(
                        self,
                        blurDeformQueryMeshes.BlurDeformQueryMeshes,
                        self.blurDeformQueryMeshesWin,
                        modal=False,
                        instanced=False,
                        lstMeshes=listResForDuplicate,
                        listToSelect=objsWithAttributes,
                        addComboMeshes=None
                    )
                    # self.blurDeformQueryMeshesWin.refreshWindow(
                    #     listResForDuplicate, objsWithAttributes, None
                    # )
                    objsToAdd = self.blurDeformQueryMeshesWin.listSelectedMeshes
                else:
                    objsToAdd = objsWithAttributes

            elif isMultiGeos:  # we need the destMesh to be selected
                added = False
                if len(selection) == 2:
                    lastGeo = selection[1]
                    if lastGeo in self.currentGeometries:
                        self.doAddNewFrame(self.currentBlurNode, lastGeo, selection[0])
                        toHide.append(selection[0])
                        added = True
                if not added:  # popup window
                    self.blurDeformQueryMeshesWin = utils.launchDialog(
                        self,
                        blurDeformQueryMeshes.BlurDeformQueryMeshes,
                        self.blurDeformQueryMeshesWin,
                        modal=True,
                        instanced=True,
                        lstMeshes=selection,
                        listToSelect=selection,
                        addComboMeshes=self.currentGeometries

                    )
                    # self.blurDeformQueryMeshesWin.refreshWindow(
                    #     selection, selection, self.currentGeometries
                    # )
                    selectedMeshes = self.blurDeformQueryMeshesWin.listSelectedMeshes
                    for geo, sourceMesh in selectedMeshes:
                        self.doAddNewFrame(self.currentBlurNode, sourceMesh, geo)
                        toHide.append(geo)
                    objsToAdd = []
            else:  # solo geo to Add, fairly StraighbtForward right ?
                if len(selection) == 2:
                    lastGeo = selection[1]
                    if lastGeo in self.currentGeometries:
                        self.doAddNewFrame(self.currentBlurNode, lastGeo, selection[0])
                        toHide.append(selection[0])
                else:
                    self.doAddNewFrame(
                        self.currentBlurNode,
                        self.currentGeometries[0],
                        selection[0],
                    )
                    toHide.append(selection[0])

        # in case of multiSelect or nothing Select
        for geo in objsToAdd:
            # get the attributes
            blurSculptNode = cmds.getAttr(geo + ".blurSculptNode")
            sourceMesh = cmds.getAttr(geo + ".sourceMesh")
            if cmds.objExists(sourceMesh) and cmds.objExists(blurSculptNode):
                self.doAddNewFrame(blurSculptNode, sourceMesh, geo)
                toHide.append(geo)

        if toHide:
            cmds.hide(toHide)
        self.exitEditMode()

        self.refresh(selectTime=True, selTime=cmds.currentTime(q=True))

    def doAddNewFrame(self, blurNode, currentGeom, targetMesh):
        print(blurNode, currentGeom, targetMesh)
        prt ,= cmds.listRelatives(targetMesh, parent=True, path=True) or [None]
        [cmds.setAttr(targetMesh+"."+att+axis, l=False) for att in "trs" for axis in " xyz"]
        if prt != currentGeom:
            cmds.parent(targetMesh, currentGeom)
        cmds.makeIdentity(targetMesh, apply=True, translate=False, rotate=True, scale=False, normal=0, preserveNormals=True)
        if prt is not None:
            cmds.parent(targetMesh, prt)
        else:
            cmds.parent(targetMesh, w=True)

        poseName = cmds.getAttr(self.currentPose + ".poseName")

        listDeformationsFrame = self.getListDeformationFrames()
        if not listDeformationsFrame:
            listDeformationsFrame = []

        cmds.blurSculpt(
            currentGeom,
            blurSculptName=self.currentBlurNode,
            addAtTime=targetMesh,
            poseName=poseName,
            offset=self.offset,
        )

    def clearVectorMvts(self, currTime):
        listDeformationsIndices = list(
            map(int, cmds.getAttr(self.currentPose + ".deformations", mi=True))
        )
        listDeformationsFrame = self.getListDeformationFrames()
        frameIndex = listDeformationsIndices[listDeformationsFrame.index(currTime)]

        dicVal = {
            "blurNode": self.currentBlurNode,
            "currentPose": self.currentPose,
        }
        dicVal["indDeform"] = frameIndex

        storedVectorsIndices = (
            cmds.getAttr(
                "{currentPose}.deformations[{indDeform}].storedVectors".format(
                    **dicVal
                ),
                mi=True,
            )
            or []
        )
        for indexGeo in storedVectorsIndices:
            dicVal["indexGeo"] = indexGeo
            cmds.removeMultiInstance(
                "{currentPose}.deformations[{indDeform}].storedVectors[{indexGeo}]".format(
                    **dicVal
                ),
                b=True,
            )

    def addEmptyFrame(self):
        deformList = cmds.getAttr(self.currentPose + ".deformations", mi=True)

        listDeformationsIndices = list(map(int, deformList)) if deformList else []
        currTime = cmds.currentTime(q=True)

        dicVal = {"pose": self.currentPose}
        dicVal["frame"] = (
            max(listDeformationsIndices) + 1 if listDeformationsIndices else 0
        )
        listDeformationsFrame = self.getListDeformationFrames()

        if currTime in listDeformationsFrame:
            res = cmds.confirmDialog(
                title="clear frame",
                m="frame {0} exists, do you want to clear mvts?\nNo Undo".format(
                    currTime
                ),
                b=("Yes", "No"),
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )
            if res == "Yes":
                self.clearVectorMvts(currTime)
        else:
            cmds.setAttr(
                "{pose}.deformations[{frame}].frame".format(**dicVal), currTime
            )
            cmds.setAttr("{pose}.deformations[{frame}].gain".format(**dicVal), 1.0)

        self.refresh(selectTime=True, selTime=currTime)

    def delete_frame(self):
        framesToDelete = sorted(
            [
                float(currentFrameItem.text(0))
                for currentFrameItem in self.uiFramesTW.selectedItems()
            ]
        )
        framesToDelete = list(map(str, framesToDelete))

        res = cmds.confirmDialog(
            title="delete",
            m="Do you want to delete the frames {0}?\nNo Undo".format(framesToDelete),
            b=("Yes", "No"),
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )
        if res == "Yes":
            for currentFrameItem in self.uiFramesTW.selectedItems():
                toDelete = str(currentFrameItem.data(0, QtCore.Qt.UserRole))
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

    def rmvMeshFromDeformer(self):
        blurNode = self.currentBlurNode
        for nd in cmds.ls(sl=True, tr=True):
            cmds.deformer(blurNode, e=True, remove=True, geometry=nd)
        self.refresh()
        if not cmds.deformer(blurNode, q=True, g=True):
            cmds.delete(blurNode)

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
        blurPose = str(item.data(0, QtCore.Qt.UserRole))

        prevName = cmds.getAttr(blurPose + ".poseName")
        if newName != prevName:
            if self.isValidName(newName, oldName=prevName):
                cmds.setAttr(blurPose + ".poseName", newName, type="string")
            else:
                with extraWidgets.toggleBlockSignals([self.uiPosesTW]):
                    item.setText(0, str(prevName))

        # check state
        isChecked = item.checkState(column) == QtCore.Qt.Checked
        prevVal = cmds.getAttr(blurPose + ".poseEnabled")
        if isChecked != prevVal:
            cmds.setAttr(blurPose + ".poseEnabled", isChecked)

    def refreshListFramesAndSelect(self, timeToSelect):
        listDeformationsFrame = sorted(self.getListDeformationFrames())
        listCurrentFrames = [
            float(self.uiFramesTW.topLevelItem(i).text(0))
            for i in range(self.uiFramesTW.topLevelItemCount())
        ]
        if listCurrentFrames != listDeformationsFrame:
            self.refreshListFrames()
            cmds.evalDeferred(partial(self.selectFrameTime, timeToSelect))

    def selectFrameTime(self, timeToSelect):
        selectionDone = False
        for i in range(self.uiFramesTW.topLevelItemCount()):
            itemFrame = self.uiFramesTW.topLevelItem(i)
            theTime = float(itemFrame.text(0))
            if theTime == timeToSelect:
                self.uiFramesTW.setCurrentItem(itemFrame)
                selectionDone = True
                break
        if not selectionDone:
            self.uiFramesTW.selectionModel().clearSelection()

    def refreshPoseInfo(self, item, prevItem):
        blurPose = str(item.data(0, QtCore.Qt.UserRole))
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
        self.uiDisconnectMatrixBTN.setVisible(deformationType == 0)

    def connectMatrix(self):
        selection = cmds.ls(sl=True, tr=True)
        if selection:
            self.uiTransformLE.setText(selection[0])
            cmds.connectAttr(
                selection[0] + ".matrix",
                self.currentPose + ".poseMatrix",
                f=True,
            )

    def disConnectMatrix(self):
        inConnections = cmds.listConnections(
            self.currentPose + ".poseMatrix", s=True, d=False, p=True
        )
        if inConnections:
            cmds.disconnectAttr(inConnections[0], self.currentPose + ".poseMatrix")
        self.uiTransformLE.setText("N/A")

    def isValidFrame(self, newFrame, oldFrame=-1):
        listDeformationsFrame = self.getListDeformationFrames()

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
        frameChannel = str(item.data(0, QtCore.Qt.UserRole))
        oldFrame = cmds.getAttr(frameChannel + ".frame")
        changeOccured = False
        if floatFrame != oldFrame:
            if self.isValidFrame(floatFrame, oldFrame=oldFrame):
                cmds.setAttr(frameChannel + ".frame", floatFrame)
                changeOccured = True
            else:
                with extraWidgets.toggleBlockSignals([self.uiFramesTW]):
                    item.setText(0, str(oldFrame))
        # check state
        isChecked = item.checkState(0) == QtCore.Qt.Checked
        prevVal = cmds.getAttr(frameChannel + ".frameEnabled")
        if isChecked != prevVal:
            cmds.setAttr(frameChannel + ".frameEnabled", isChecked)

        if changeOccured:
            self.refreshListFramesAndSelect(floatFrame)

    def selectFrameInTimeLine(self):
        with extraWidgets.toggleBlockSignals([self.uiFramesTW]):
            first = True
            selectedItems = self.uiFramesTW.selectedItems()
            for item in selectedItems:
                indexFrame = self.uiFramesTW.indexOfTopLevelItem(item)
                self.blurTimeSlider.listKeys[indexFrame].select(
                    addSel=not first, selectInTree=False
                )
                first = False

    # ---------------------- display of ARRAY --------------------------------------
    def addKeyToTimePort(self, listDeformationsFrame):
        if self.addTimeLine:
            self.blurTimeSlider.deleteKeys()
            for keyTime, isEmpty in listDeformationsFrame:
                self.blurTimeSlider.addDisplayKey(keyTime, isEmpty=isEmpty)

    def refreshListFrames(self):
        with extraWidgets.toggleBlockSignals([self.uiFramesTW]):
            self.uiFramesTW.clear()
            self.uiFramesTW.setColumnCount(4)
            self.uiFramesTW.setHeaderLabels(["frame", "\u00D8", "gain", "offset"])

            listDeformationsFrame = self.getListDeformationFrames()
            listFramesViewPort = []
            if listDeformationsFrame:
                listDeformationsIndices = cmds.getAttr(
                    self.currentPose + ".deformations", mi=True
                )
                if not listDeformationsIndices:
                    listDeformationsIndices = []

                listDeformationsFrameandIndices = [
                    (listDeformationsFrame[i], listDeformationsIndices[i])
                    for i in range(len(listDeformationsFrame))
                ]
                listDeformationsFrameandIndices.sort()
                for (
                    deformFrame,
                    logicalFrameIndex,
                ) in listDeformationsFrameandIndices:
                    frameItem = QtWidgets.QTreeWidgetItem()
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
                        self.currentPose
                        + ".deformations[{0}]".format(logicalFrameIndex),
                    )
                    frameItem.setText(2, "0.")
                    frameItem.setText(3, "0.")

                    storedVectorsIndices = (
                        cmds.getAttr(
                            self.currentPose
                            + ".deformations[{0}].storedVectors".format(
                                logicalFrameIndex
                            ),
                            mi=True,
                        )
                        or []
                    )
                    vectorMovementsIndices = []
                    for ind in storedVectorsIndices:
                        vectorMovementsIndices = cmds.getAttr(
                            self.currentPose
                            + ".deformations[{}].storedVectors[{}].multiVectorMovements".format(
                                logicalFrameIndex, ind
                            ),
                            mi=True,
                        )
                        if vectorMovementsIndices:
                            break
                    if not vectorMovementsIndices:
                        frameItem.setBackground(0, QtGui.QBrush(self.blueCol))
                        frameItem.setText(1, "\u00D8")
                        listFramesViewPort.append((deformFrame, True))
                    else:
                        listFramesViewPort.append((deformFrame, False))

                    self.uiFramesTW.addTopLevelItem(frameItem)
                    newWidgetGain = extraWidgets.SpinnerWidget(
                        self.currentPose
                        + ".deformations[{0}].gain".format(logicalFrameIndex),
                        singleStep=0.1,
                        precision=2,
                    )
                    newWidgetGain.setMinimumHeight(20)
                    newWidgetOffset = extraWidgets.SpinnerWidget(
                        self.currentPose
                        + ".deformations[{0}].offset".format(logicalFrameIndex),
                        singleStep=0.1,
                        precision=2,
                    )
                    self.uiFramesTW.setItemWidget(frameItem, 2, newWidgetGain)
                    self.uiFramesTW.setItemWidget(frameItem, 3, newWidgetOffset)

            if self.addTimeLine:
                self.addKeyToTimePort(listFramesViewPort)

            vh = self.uiFramesTW.header()
            vh.setStretchLastSection(False)
            QtCompat.QHeaderView.setSectionResizeMode(vh, vh.Stretch)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 0, vh.Stretch)
            self.uiFramesTW.setColumnWidth(1, 20)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 1, vh.Fixed)
            self.uiFramesTW.setColumnWidth(2, 50)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 2, vh.Fixed)
            self.uiFramesTW.setColumnWidth(3, 50)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 3, vh.Fixed)
            cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 1, 20))
            cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 2, 50))
            cmds.evalDeferred(partial(self.uiFramesTW.setColumnWidth, 3, 50))

    def refreshListPoses(self, selectLast=False):
        with extraWidgets.toggleBlockSignals([self.uiPosesTW]):
            self.currentPose = ""
            self.uiPosesTW.clear()
            self.uiFramesTW.clear()

            self.uiPosesTW.setColumnCount(3)
            self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])

            listPoses = cmds.blurSculpt(
                self.currentBlurNode, query=True, listPoses=True
            )
            if not listPoses:
                return
            dicVal = {"blurNode": self.currentBlurNode}

            posesIndices = list(
                map(int, cmds.getAttr(self.currentBlurNode + ".poses", mi=True))
            )
            for logicalInd in posesIndices:
                dicVal["indPose"] = logicalInd
                thePose = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].poseName".format(**dicVal)
                )

                channelItem = QtWidgets.QTreeWidgetItem()
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
                    0,
                    QtCore.Qt.UserRole,
                    "{blurNode}.poses[{indPose}]".format(**dicVal),
                )

                newWidgetGain = extraWidgets.SpinnerWidget(
                    "{blurNode}.poses[{indPose}].poseGain".format(**dicVal),
                    singleStep=0.1,
                    precision=2,
                )
                newWidgetGain.setMinimumHeight(20)
                newWidgetOffset = extraWidgets.SpinnerWidget(
                    "{blurNode}.poses[{indPose}].poseOffset".format(**dicVal),
                    singleStep=0.1,
                    precision=2,
                )
                self.uiPosesTW.setItemWidget(channelItem, 1, newWidgetGain)
                self.uiPosesTW.setItemWidget(channelItem, 2, newWidgetOffset)

            vh = self.uiPosesTW.header()
            vh.setStretchLastSection(False)
            # Qt.py compat
            QtCompat.QHeaderView.setSectionResizeMode(vh, vh.Stretch)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 0, vh.Stretch)

            self.uiPosesTW.setColumnWidth(1, 50)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 1, vh.Fixed)
            self.uiPosesTW.setColumnWidth(2, 50)
            QtCompat.QHeaderView.setSectionResizeMode(vh, 2, vh.Fixed)
            cmds.evalDeferred(partial(self.uiPosesTW.setColumnWidth, 1, 50))
            cmds.evalDeferred(partial(self.uiPosesTW.setColumnWidth, 2, 50))

        if len(listPoses) > 0:
            if selectLast:
                self.uiPosesTW.setCurrentItem(channelItem)
            else:
                self.uiPosesTW.setCurrentItem(self.uiPosesTW.topLevelItem(0))

    def changedSelection(self, item, column):
        self.currentBlurNode = str(item.text(0))
        self.currentGeometries, self.currentGeometriesIndices = self.getGeom(
            self.currentBlurNode, transform=True
        )
        self.blurTimeSlider.deleteKeys()
        self.uiEnvelopeWg.move(50, 0)
        self.uiEnvelopeWg.resize(50, 18)

        if not self.uiBlurNodesTW.multiSelection:
            self.uiEnvelopeWg.doConnectAttrSpinner(self.currentBlurNode + ".envelope")
            self.refreshListPoses()
        else:
            selectedItems = [
                el.text(0) + ".envelope" for el in self.uiBlurNodesTW.selectedItems()
            ]
            selectedItems.append(self.currentBlurNode + ".envelope")
            selectedItems = list(set(selectedItems))
            self.uiEnvelopeWg.doConnectAttrSpinner(selectedItems)

        self.uiEnvelopeWg.theSpinner.setRange(0, 1)

    def fillTreeOfBlurNodes(self):
        with extraWidgets.toggleBlockSignals([self.uiBlurNodesTW]):
            self.uiBlurNodesTW.clear()
            self.uiBlurNodesTW.setColumnCount(2)
            self.uiBlurNodesTW.setHeaderLabels(["blurSculpt", "mesh"])
            self.uiBlurNodesTW.setExpandsOnDoubleClick(False)

            blurNodes = cmds.ls(type="blurSculpt")
            blurNodesSorted = []
            for blrNode in blurNodes:
                geos, geoIndices = self.getGeom(blrNode, transform=True)
                if geos:
                    blurNodesSorted.append((" - ".join(geos), blrNode))
            blurNodesSorted.sort()

            for geom, blrNode in blurNodesSorted:
                channelItem = QtWidgets.QTreeWidgetItem()
                channelItem.setText(0, blrNode)
                channelItem.setText(1, geom)
                self.uiBlurNodesTW.addTopLevelItem(channelItem)

        for i in range(2):
            self.uiBlurNodesTW.resizeColumnToContents(i)

    def doubleClickChannel(self, item, column):
        blurNode = str(item.text(0))
        if column == 1:
            geos, geosIndices = self.getGeom(blurNode, transform=True)
            toSelect = geos
        else:
            toSelect = blurNode
        cmds.select(toSelect)

    def getGeom(self, currentBlurNode, transform=False):
        lstMeshes = cmds.deformer(currentBlurNode, q=True, g=True)
        if transform and lstMeshes:
            lstMeshes = [
                cmds.listRelatives(msh, path=True, p=True)[0] for msh in lstMeshes
            ]
        lstIndices = cmds.deformer(currentBlurNode, q=True, gi=True)
        return (lstMeshes, lstIndices)

    def doSelectBlurNode(self, theBlurNode):
        print(" doSelectBlurNode [{}]".format(theBlurNode))
        blurNodes = [
            self.uiBlurNodesTW.topLevelItem(ind).text(0)
            for ind in range(self.uiBlurNodesTW.topLevelItemCount())
        ]
        if theBlurNode in blurNodes:
            ind = blurNodes.index(theBlurNode)
            item = self.uiBlurNodesTW.topLevelItem(ind)
            self.uiBlurNodesTW.setCurrentItem(item)
            self.changedSelection(item, 0)

    def selectFromScene(self):
        currentSel = cmds.ls(sl=True)
        if len(currentSel) == 1:
            self.uiBlurNodesTW.setSelectionMode(1)
            self.uiBlurNodesTW.multiSelection = False
            obj = currentSel
            hist = cmds.listHistory(obj)
            if hist:
                blurSculpts = cmds.ls(hist, type="blurSculpt")

            if hist and blurSculpts:
                self.doSelectBlurNode(blurSculpts[0])
            else:
                self.uiBlurNodesTW.selectionModel().clearSelection()
                with extraWidgets.toggleBlockSignals(
                    [self.uiBlurNodesTW, self.uiPosesTW, self.uiFramesTW]
                ):
                    self.currentPose = ""
                    self.currentGeom = ""
                    self.uiPosesTW.clear()
                    self.uiFramesTW.clear()
                    self.uiPosesTW.setColumnCount(3)
                    self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])

    # ----------------------- EDIT MODE  --------------------------------------------------
    def enterEditMode(self):
        self.resForDuplicate = []
        geoAndIndex = list(zip(self.currentGeometries, self.currentGeometriesIndices))
        for geo, geoIndex in geoAndIndex:
            nameSpaceSplit = geo.split(":")
            dupName = "EDIT_" + nameSpaceSplit[-1]
            dup = cmds.duplicate(geo, name=dupName)[0]
            cmds.makeIdentity(dup, apply=True, translate=False, rotate=True, scale=False, normal=0, preserveNormals=True)
            cmds.addAttr(dup, longName="blurSculptNode", dataType="string")
            cmds.setAttr(dup + ".blurSculptNode", edit=True, keyable=True)
            cmds.setAttr(dup + ".blurSculptNode", self.currentBlurNode, type="string")
            cmds.addAttr(dup, longName="sourceMesh", dataType="string")
            cmds.setAttr(dup + ".sourceMesh", edit=True, keyable=True)
            cmds.setAttr(dup + ".sourceMesh", geo, type="string")
            cmds.addAttr(dup, longName="blurSculptIndex", attributeType="long")
            cmds.setAttr(dup + ".blurSculptIndex", edit=True, keyable=True)
            cmds.setAttr(dup + ".blurSculptIndex", geoIndex)
            self.resForDuplicate.append(dup)

        cmds.select(self.currentGeometries)
        cmds.HideSelectedObjects()
        cmds.select(self.resForDuplicate)

    def exitEditMode(self):
        listResForDuplicate = cmds.ls(self.resForDuplicate)
        if not self.keepShapes and listResForDuplicate:
            cmds.delete(listResForDuplicate)
            self.resForDuplicate = []
            doRename = False
        else:
            doRename = True

        if doRename and listResForDuplicate:
            for geo in listResForDuplicate:
                poseName = cmds.getAttr(self.currentPose + ".poseName")
                geoIndex = (
                    cmds.getAttr(geo + ".blurSculptIndex")
                    if cmds.attributeQuery("blurSculptIndex", node=geo, ex=True)
                    else -1
                )
                if geoIndex > -1:
                    newName = "{}_Ind{}_{}_f{}_".format(
                        self.currentBlurNode,
                        geoIndex,
                        poseName,
                        int(cmds.currentTime(q=True)),
                    )
                else:
                    newName = "{}_{}_f{}_".format(
                        self.currentBlurNode,
                        poseName,
                        int(cmds.currentTime(q=True)),
                    )
                cmds.rename(geo, newName)
            self.resForDuplicate = []

        cmds.showHidden(self.currentGeometries, a=True)
        cmds.selectMode(object=True)

    # ------------------- REFRESH ----------------------------------------------------

    def refresh(self, selectTime=False, selTime=0.0):
        with extraWidgets.toggleBlockSignals(
            [self.uiBlurNodesTW, self.uiPosesTW, self.uiFramesTW]
        ):
            self.uiPosesTW.clear()
            self.uiFramesTW.clear()

            currentPose = self.currentPose

            self.uiPosesTW.setColumnCount(3)
            self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])
            self.uiFramesTW.setColumnCount(4)
            self.uiFramesTW.setHeaderLabels(["frame", "\u00D8", "gain", "offset"])

            self.fillTreeOfBlurNodes()

            blurNodes = [
                self.uiBlurNodesTW.topLevelItem(ind).text(0)
                for ind in range(self.uiBlurNodesTW.topLevelItemCount())
            ]

            if self.currentBlurNode in blurNodes:
                ind = blurNodes.index(self.currentBlurNode)
                item = self.uiBlurNodesTW.topLevelItem(ind)
                self.uiBlurNodesTW.setCurrentItem(item)
                self.changedSelection(item, 0)

                foundPose = False
                for i in range(self.uiPosesTW.topLevelItemCount()):
                    itemPose = self.uiPosesTW.topLevelItem(i)
                    thePose = str(itemPose.data(0, QtCore.Qt.UserRole))
                    if thePose == currentPose:
                        foundPose = True
                        self.uiPosesTW.setCurrentItem(itemPose)
                        break
                if not foundPose and currentPose != "":
                    self.currentPose = ""
                    self.uiPosesTW.selectionModel().clearSelection()

            else:
                self.currentBlurNode = ""
                self.currentGeom = ""
                self.currentPose = ""

        if selectTime:
            self.selectFrameTime(selTime)

    def resizePoseInfo(self, checkState):
        if checkState:
            self.uiPoseGB.setMaximumHeight(1000)
        else:
            self.uiPoseGB.setMaximumHeight(20)

    # ------------------- POPUP ----------------------------------------------------
    def create_popup_menu(self, parent=None):
        self.popup_menu = QtWidgets.QMenu(parent)
        self.popup_menu.addAction(
            utils.ICONS["toFrame"], "jumpToFrame (Mid click)", self.jumpToFrame
        )
        self.popup_menu.addAction(
            "duplicate frame (Ctrl Drag in timeLine)", self.doDuplicate
        )
        self.popup_menu.addAction("select influenced vertices", self.selectVertices)
        self.popup_menu.addSeparator()
        self.popup_menu.addAction(
            "set vertices to  " + "\u00D8" + "  blank   (NO UNDO)",
            self.removeSelectedVerticesFromFrame,
        )
        self.popup_menu.addAction(
            "set vertices to inbetween (NO UNDO)",
            self.setSelectedVerticestoInBetweenFrame,
        )
        self.popup_menu.addSeparator()
        self.popup_menu.addAction("copy deltas", self.deltasCopy)
        self.popup_menu.addAction("paste deltas", self.deltasPaste)
        self.popup_menu.addSeparator()
        self.popup_menu.addAction("bake gain", partial(self.bake, "gain"))
        self.popup_menu.addAction("bake offset", partial(self.bake, "offset"))
        self.popup_menu.addSeparator()
        self.popup_menu.addAction(
            utils.ICONS["Delete"], "delete (NO UNDO)", self.delete_frame
        )

        self.popup_option = QtWidgets.QMenu(parent)
        newAction = self.popup_option.addAction("keep Shapes", self.doKeepShapes)
        newAction.setCheckable(True)
        self.popup_option.addSeparator()
        self.popup_option.addAction(
            utils.ICONS["backUp"], "backUp all Shapes", self.backUp
        )
        self.popup_option.addAction(
            utils.ICONS["restore"], "restore from backUp", self.restoreBackUp
        )
        self.popup_option.addSeparator()
        self.popup_option.addAction("store xml file", self.callSaveXml)
        self.popup_option.addAction("retrieve xml file", self.callOpenXml)
        self.popup_option.addSeparator()
        self.popup_option.addAction(
            "set distance offset [{0}]".format(self.offset),
            self.setDistanceOffset,
        )

        if cmds.optionVar(exists="blurScluptKeep"):
            setChecked = cmds.optionVar(q="blurScluptKeep") == 1
        else:
            setChecked = False
        self.keepShapes = setChecked
        newAction.setChecked(setChecked)
        self.uiOptionsBTN.mousePressEvent = self.popMenuMousePressEvent

    def setDistanceOffset(self):
        cmds.promptDialog(m="set distance", text="{0}".format(self.offset))
        val = cmds.promptDialog(q=True, text=True)
        try:
            val = float(val)
            self.offset = val
            self.popup_option.actions()[5].setText(
                "set distance offset [{0}]".format(self.offset)
            )
            cmds.optionVar(floatValue=["blurScluptOffset", self.offset])
        except Exception:
            pass

    def popMenuMousePressEvent(self, event):
        self.popup_option.exec_(event.globalPos())

    def storeXmlFileOfPoses(self):
        sceneName = cmds.file(q=True, sceneName=True)
        splt = sceneName.split("/")
        startDir = "/".join(splt[:-1])
        res = cmds.fileDialog2(
            fileMode=0,
            dialogStyle=1,
            caption="save data",
            startingDirectory=startDir,
        )
        if res:
            destinationFile = res.pop()
            if not destinationFile.endswith(".xml"):
                destinationFile = destinationFile.split(".")[0] + ".xml"

        else:
            return

        with extraWidgets.WaitCursorCtxt():
            doc = minidom.Document()
            ALL_tag = doc.createElement("ALL")
            doc.appendChild(ALL_tag)
            created_tag = self.storeInfoBlurSculpt(doc, self.currentBlurNode)
            ALL_tag.appendChild(created_tag)

            with codecs.open(destinationFile, "w", "utf-8") as out:
                doc.writexml(out, indent="\n", addindent="\t", newl="")

    def retrieveXml(self):
        sceneName = cmds.file(q=True, sceneName=True)
        splt = sceneName.split("/")
        startDir = "/".join(splt[:-1])
        res = cmds.fileDialog2(
            fileMode=1,
            dialogStyle=1,
            caption="retrieve data",
            startingDirectory=startDir,
        )

        if res:
            with extraWidgets.WaitCursorCtxt():
                sourceFile = res.pop()
                if os.path.isfile(sourceFile):
                    tree = ElementTree.parse(sourceFile)
                    root = tree.getroot()
                    self.retrieveblurXml(root)

    def retrieveblurXml(self, root):
        dicVal = {"blurNode": self.currentBlurNode}

        pses = cmds.getAttr(self.currentBlurNode + ".poses", mi=True)
        dicPoses = {}
        newInd = 0
        if pses:
            posesIndices = list(map(int, pses))
            for logicalInd in posesIndices:
                dicVal["indPose"] = logicalInd
                poseName = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].poseName".format(**dicVal)
                )
                dicPoses[poseName] = logicalInd
            newInd = max(posesIndices) + 1

        for blurNode_tag in list(iter(root)):
            blurName = blurNode_tag.get("name")
            print(blurName)
            for pose_tag in list(iter(blurNode_tag)):
                poseName = pose_tag.get("poseName")
                print(poseName)

                # access the pose Index
                if poseName not in dicPoses:  # create it
                    dicVal["indPose"] = newInd
                    cmds.setAttr(
                        "{blurNode}.poses[{indPose}].poseName".format(**dicVal),
                        poseName,
                        type="string",
                    )
                    dicPoses[poseName] = newInd
                    newInd += 1
                    # do the connection and type
                    poseEnabled = pose_tag.get("poseEnabled") == "True"
                    poseGain = float(pose_tag.get("poseGain"))
                    poseOffset = float(pose_tag.get("poseOffset"))
                    cmds.setAttr(
                        "{blurNode}.poses[{indPose}].poseEnabled".format(**dicVal),
                        poseEnabled,
                    )
                    cmds.setAttr(
                        "{blurNode}.poses[{indPose}].poseGain".format(**dicVal),
                        poseGain,
                    )
                    cmds.setAttr(
                        "{blurNode}.poses[{indPose}].poseOffset".format(**dicVal),
                        poseOffset,
                    )

                    deformType = int(pose_tag.get("deformType"))
                    cmds.setAttr(
                        "{blurNode}.poses[{indPose}].deformationType".format(**dicVal),
                        deformType,
                    )
                    poseMatrixConn = pose_tag.get("poseMatrix")
                    if cmds.objExists(poseMatrixConn):
                        try:
                            cmds.connectAttr(
                                poseMatrixConn,
                                "{blurNode}.poses[{indPose}].poseMatrix".format(
                                    **dicVal
                                ),
                                f=True,
                            )
                        except Exception:
                            pass
                else:
                    dicVal["indPose"] = dicPoses[poseName]

                dicFrames = {}
                newFrameInd = 0
                listDeformationsIndices = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].deformations".format(**dicVal),
                    mi=True,
                )
                if listDeformationsIndices:
                    for logicalFrameIndex in listDeformationsIndices:
                        frame = cmds.getAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                                **dicVal
                            )
                        )
                        dicFrames[frame] = logicalFrameIndex
                    newFrameInd = max(listDeformationsIndices) + 1

                for frame_tag in list(iter(pose_tag)):
                    frame = float(frame_tag.get("frame"))
                    if frame not in dicFrames:
                        dicVal["frameInd"] = newFrameInd
                        newFrameInd += 1

                        gain = float(frame_tag.get("gain"))
                        offset = float(frame_tag.get("offset"))
                        frameEnabled = frame_tag.get("frameEnabled") == "True"
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format(
                                **dicVal
                            ),
                            gain,
                        )
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format(
                                **dicVal
                            ),
                            offset,
                        )
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format(
                                **dicVal
                            ),
                            frameEnabled,
                        )
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                                **dicVal
                            ),
                            frame,
                        )
                    else:
                        dicVal["frameInd"] = dicFrames[frame]
                        # first clear
                        frameName = "{blurNode}.poses[{indPose}].deformations[{frameInd}]".format(
                            **dicVal
                        )
                        mvtIndices = cmds.getAttr(
                            frameName + ".vectorMovements", mi=True
                        )
                        if mvtIndices:
                            mvtIndices = list(map(int, mvtIndices))
                            for indVtx in mvtIndices:
                                cmds.removeMultiInstance(
                                    frameName + ".vectorMovements[{0}]".format(indVtx),
                                    b=True,
                                )

                    vector_tag = list(iter(frame_tag))[0]
                    for vectag in list(iter(vector_tag)):
                        index = int(vectag.get("index"))
                        dicVal["vecInd"] = index
                        value = vectag.get("value")
                        floatVal = list(map(float, value[1:-1].split(", ")))
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].vectorMovements[{vecInd}]".format(
                                **dicVal
                            ),
                            *floatVal
                        )

    def storeInfoBlurSculpt(self, doc, blurNode, inputPoseFramesIndices=None):
        blurNode_tag = doc.createElement("blurSculpt")
        blurNode_tag.setAttribute("name", blurNode)
        geos, geoIndices = self.getGeom(blurNode, transform=True)
        # geom
        geom = " - ".join(geos)
        geomIndices = " - ".join(map(str, geoIndices))
        blurNode_tag.setAttribute("geom", geom)
        blurNode_tag.setAttribute("geomIndices", geomIndices)
        nbVertices = cmds.polyEvaluate(geom, v=True)
        blurNode_tag.setAttribute("nbVertices", nbVertices)

        listPoses = cmds.blurSculpt(blurNode, query=True, listPoses=True)
        if not listPoses:
            return blurNode_tag
        dicVal = {"blurNode": blurNode}

        posesIndices = list(map(int, cmds.getAttr(blurNode + ".poses", mi=True)))
        if inputPoseFramesIndices:
            posesIndices = list(inputPoseFramesIndices.keys())

        # first store positions
        for logicalInd in posesIndices:
            dicVal["indPose"] = logicalInd

            thePose = cmds.getAttr(
                "{blurNode}.poses[{indPose}].poseName".format(**dicVal)
            )
            poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format(**dicVal)
            poseGain = "{blurNode}.poses[{indPose}].poseGain".format(**dicVal)
            poseOffset = "{blurNode}.poses[{indPose}].poseOffset".format(**dicVal)
            isEnabled = cmds.getAttr(poseAttr)
            poseGainVal = cmds.getAttr(poseGain)
            poseOffsetVal = cmds.getAttr(poseOffset)

            pose_tag = doc.createElement("pose")
            pose_tag.setAttribute("poseEnabled", str(isEnabled))
            pose_tag.setAttribute("poseGain", str(poseGainVal))
            pose_tag.setAttribute("poseOffset", str(poseOffsetVal))
            pose_tag.setAttribute("poseName", str(thePose))

            blurNode_tag.appendChild(pose_tag)

            deformType = cmds.getAttr(
                "{blurNode}.poses[{indPose}].deformationType".format(**dicVal)
            )
            pose_tag.setAttribute("deformType", str(deformType))

            inConnections = cmds.listConnections(
                "{blurNode}.poses[{indPose}].poseMatrix".format(**dicVal),
                s=True,
                d=False,
                p=True,
            )
            if not inConnections:
                val = "N/A"
            else:
                val = inConnections[0]
            pose_tag.setAttribute("poseMatrix", str(val))

            listDeformationsIndices = cmds.getAttr(
                "{blurNode}.poses[{indPose}].deformations".format(**dicVal),
                mi=True,
            )
            if inputPoseFramesIndices:
                listDeformationsIndices = inputPoseFramesIndices[logicalInd]

            if not listDeformationsIndices:
                continue

            for logicalFrameIndex in listDeformationsIndices:
                dicVal["frameInd"] = logicalFrameIndex
                frame = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                        **dicVal
                    )
                )

                # store vals
                gain = (
                    "{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format(
                        **dicVal
                    )
                )
                offset = "{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format(
                    **dicVal
                )
                gainVal = cmds.getAttr(gain)
                offsetVal = cmds.getAttr(offset)

                frameEnabled = "{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format(
                    **dicVal
                )
                frameEnabledVal = cmds.getAttr(frameEnabled)

                frame_tag = doc.createElement("frame")
                frame_tag.setAttribute("frame", str(frame))
                frame_tag.setAttribute("gain", str(gainVal))
                frame_tag.setAttribute("offset", str(offsetVal))
                frame_tag.setAttribute("frameEnabled", str(frameEnabledVal))

                pose_tag.appendChild(frame_tag)
                #####################################################################

                storedVectorsIndices = (
                    cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors".format(
                            **dicVal
                        ),
                        mi=True,
                    )
                    or []
                )
                storeVectore_tag = doc.createElement("storedVectors")
                frame_tag.appendChild(storeVectore_tag)

                for indexGeo in storedVectorsIndices:
                    dicVal["indexGeo"] = indexGeo
                    indicesVectorMvt = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors[{indexGeo}].multiVectorMovements".format(
                            **dicVal
                        ),
                        mi=True,
                    )
                    if indicesVectorMvt:
                        vector_tag = doc.createElement("multiVectorMovements")
                        vector_tag.setAttribute("indexGeo", str(indexGeo))
                        for vecInd in indicesVectorMvt:
                            dicVal["vecInd"] = vecInd
                            (mvt,) = cmds.getAttr(
                                "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors[{indexGeo}].multiVectorMovements[{vecInd}]".format(
                                    **dicVal
                                )
                            )
                            vectag = doc.createElement("vectorMovements")
                            vectag.setAttribute("index", str(vecInd))
                            vectag.setAttribute("value", str(mvt))
                            vector_tag.appendChild(vectag)
                        storeVectore_tag.appendChild(vector_tag)

        return blurNode_tag

    def backUp(self, withBlendShape=True):
        selectedItems = [el.text(0) for el in self.uiBlurNodesTW.selectedItems()]
        createdShapes = []
        with extraWidgets.MayaProgressBar(
            maxValue=len(selectedItems),
            status="backUp ...",
            QTprogress=self.progressBar,
            frontWindow=False,
        ) as pBar:
            for theBlurNode in selectedItems:
                if not pBar.update():
                    break
                blurGrp = cmds.createNode("transform", n="{0}_".format(theBlurNode))

                geos, geoIndices = self.getGeom(theBlurNode, transform=True)
                geom = " - ".join(geos)
                geomIndices = " - ".join(map(str, geoIndices))
                indicesMeshes = sorted(zip(geos, geoIndices))
                blurNodeIndexToMesh = {}
                for msh, ind in indicesMeshes:
                    blurNodeIndexToMesh[ind] = msh
                # -------------------------------------

                cmds.addAttr(blurGrp, longName="meshName", dataType="string")
                cmds.setAttr(blurGrp + ".meshName", edit=True, keyable=True)
                cmds.setAttr(blurGrp + ".meshName", geom, type="string")

                cmds.addAttr(blurGrp, longName="meshIndices", dataType="string")
                cmds.setAttr(blurGrp + ".meshIndices", edit=True, keyable=True)
                cmds.setAttr(blurGrp + ".meshIndices", geomIndices, type="string")

                listPoses = cmds.blurSculpt(theBlurNode, query=True, listPoses=True)
                if not listPoses:
                    return
                dicVal = {"blurNode": theBlurNode}

                posesIndices = list(
                    map(int, cmds.getAttr(theBlurNode + ".poses", mi=True))
                )
                # first store positions
                storedStates = {}
                for logicalInd in posesIndices:
                    dicVal["indPose"] = logicalInd
                    poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format(
                        **dicVal
                    )
                    isEnabled = cmds.getAttr(poseAttr)
                    cmds.setAttr(poseAttr, False)

                    storedStates[poseAttr] = isEnabled

                    poseGain = "{blurNode}.poses[{indPose}].poseGain".format(**dicVal)
                    poseOffset = "{blurNode}.poses[{indPose}].poseOffset".format(
                        **dicVal
                    )
                    poseGainVal = cmds.getAttr(poseGain)
                    poseOffsetVal = cmds.getAttr(poseOffset)
                    cmds.setAttr(poseGain, 1.0)
                    cmds.setAttr(poseOffset, 0.0)

                    storedStates[poseGain] = poseGainVal
                    storedStates[poseOffset] = poseOffsetVal

                for logicalInd in posesIndices:
                    dicVal["indPose"] = logicalInd
                    thePose = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].poseName".format(**dicVal)
                    )
                    thePoseGrp = cmds.createNode(
                        "transform",
                        n="{0}_{1}_".format(theBlurNode, thePose),
                        p=blurGrp,
                    )

                    cmds.addAttr(
                        thePoseGrp,
                        longName="deformationType",
                        attributeType="enum",
                        enumName="local:tangent:",
                    )
                    cmds.setAttr(
                        thePoseGrp + ".deformationType", edit=True, keyable=True
                    )
                    deformType = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformationType".format(**dicVal)
                    )
                    cmds.setAttr(thePoseGrp + ".deformationType", deformType)

                    inConnections = cmds.listConnections(
                        "{blurNode}.poses[{indPose}].poseMatrix".format(**dicVal),
                        s=True,
                        d=False,
                        p=True,
                    )
                    if not inConnections:
                        val = "N/A"
                    else:
                        val = inConnections[0]
                    cmds.addAttr(thePoseGrp, longName="poseMatrix", dataType="string")
                    cmds.setAttr(thePoseGrp + ".poseMatrix", edit=True, keyable=True)
                    cmds.setAttr(thePoseGrp + ".poseMatrix", val, type="string")

                    listDeformationsIndices = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformations".format(**dicVal),
                        mi=True,
                    )
                    if not listDeformationsIndices:
                        continue
                    poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format(
                        **dicVal
                    )
                    cmds.setAttr(poseAttr, True)

                    # add attributes -------------------------------------------------------------------------------------
                    for att in ["poseGain", "poseOffset", "poseEnabled"]:
                        if att == "poseEnabled":
                            cmds.addAttr(thePoseGrp, longName=att, attributeType="bool")
                        else:
                            cmds.addAttr(
                                thePoseGrp, longName=att, attributeType="float"
                            )
                        cmds.setAttr(thePoseGrp + "." + att, edit=True, keyable=True)
                        dicVal["att"] = att
                        realAtt = "{blurNode}.poses[{indPose}].{att}".format(**dicVal)
                        val = storedStates[realAtt]  # cmds.getAttr (realAtt)
                        cmds.setAttr(thePoseGrp + "." + att, val)
                        inConn = cmds.listConnections(
                            realAtt, s=True, d=False, c=True, scn=False
                        )
                        if inConn:
                            cmds.connectAttr(inConn[0], thePoseGrp + "." + att)

                    # for all frames -------------------------------------------------------------------------------------
                    for logicalFrameIndex in listDeformationsIndices:
                        dicVal["frameInd"] = logicalFrameIndex
                        frame = cmds.getAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                                **dicVal
                            )
                        )

                        # store vals --------------------------------------------------------------------------------------------
                        gain = "{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format(
                            **dicVal
                        )
                        offset = "{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format(
                            **dicVal
                        )
                        gainVal = cmds.getAttr(gain)
                        offsetVal = cmds.getAttr(offset)
                        cmds.setAttr(gain, 1.0)
                        cmds.setAttr(offset, 0.0)

                        storedStates[gain] = gainVal
                        storedStates[offset] = offsetVal

                        frameEnabled = "{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format(
                            **dicVal
                        )
                        frameEnabledVal = cmds.getAttr(frameEnabled)
                        cmds.setAttr(frameEnabled, True)

                        storedStates[frameEnabled] = frameEnabledVal
                        # end vals --------------------------------------------------------------------------------------------
                        cmds.currentTime(frame)

                        frameName = "{}_{}_f{}_".format(
                            theBlurNode, thePose, int(frame)
                        )
                        theFrameGrp = cmds.createNode(
                            "transform", n=frameName, p=thePoseGrp
                        )

                        storedVectorsIndices = (
                            cmds.getAttr(
                                "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors".format(
                                    **dicVal
                                ),
                                mi=True,
                            )
                            or []
                        )
                        for indGeo in storedVectorsIndices:
                            if indGeo in geoIndices:  # if it's actually valid
                                theGeo = blurNodeIndexToMesh[int(indGeo)]
                                theGeoShortName = theGeo.split(":")[-1]
                                frameGeoName = "{}_{}_f{}_{}".format(
                                    theBlurNode,
                                    thePose,
                                    int(frame),
                                    theGeoShortName,
                                )
                                if withBlendShape:
                                    (deform,) = cmds.duplicate(theGeo, name="deform")
                                    cmds.setAttr(theBlurNode + ".envelope", 0)
                                    (frameDup,) = cmds.duplicate(
                                        theGeo, name=frameGeoName
                                    )
                                    cmds.setAttr(theBlurNode + ".envelope", 1)
                                    (newBS,) = cmds.blendShape(deform, frameDup)
                                    cmds.setAttr(newBS + ".w[0]", 1)
                                    cmds.delete(
                                        cmds.ls(
                                            cmds.listHistory(newBS),
                                            type="tweak",
                                        )
                                    )
                                    cmds.delete(deform)
                                else:
                                    (frameDup,) = cmds.duplicate(
                                        theGeo, name=frameGeoName
                                    )

                                cmds.addAttr(
                                    frameDup,
                                    longName="blurSculptNode",
                                    dataType="string",
                                )
                                cmds.setAttr(
                                    frameDup + ".blurSculptNode",
                                    edit=True,
                                    keyable=True,
                                )
                                cmds.setAttr(
                                    frameDup + ".blurSculptNode",
                                    theBlurNode,
                                    type="string",
                                )
                                cmds.addAttr(
                                    frameDup,
                                    longName="sourceMesh",
                                    dataType="string",
                                )
                                cmds.setAttr(
                                    frameDup + ".sourceMesh",
                                    edit=True,
                                    keyable=True,
                                )
                                cmds.setAttr(
                                    frameDup + ".sourceMesh",
                                    theGeo,
                                    type="string",
                                )
                                cmds.addAttr(
                                    frameDup,
                                    longName="blurSculptIndex",
                                    attributeType="long",
                                )
                                cmds.setAttr(
                                    frameDup + ".blurSculptIndex",
                                    edit=True,
                                    keyable=True,
                                )
                                cmds.setAttr(frameDup + ".blurSculptIndex", indGeo)

                                frameDup = cmds.parent(frameDup, theFrameGrp)
                                print(frameDup, frameGeoName)
                                cmds.hide(frameDup)
                                frameDup = str(frameDup[0])
                                createdShapes.append(frameDup)
                        # add attributes -------------------------------------------------------------------------------------
                        for att in ["gain", "offset", "frameEnabled"]:
                            if att == "frameEnabled":
                                cmds.addAttr(
                                    theFrameGrp,
                                    longName=att,
                                    attributeType="bool",
                                )
                            else:
                                cmds.addAttr(
                                    theFrameGrp,
                                    longName=att,
                                    attributeType="float",
                                )
                            cmds.setAttr(
                                theFrameGrp + "." + att, edit=True, keyable=True
                            )
                            dicVal["att"] = att
                            realAtt = "{blurNode}.poses[{indPose}].deformations[{frameInd}].{att}".format(
                                **dicVal
                            )
                            val = storedStates[realAtt]  # cmds.getAttr (realAtt)
                            cmds.setAttr(theFrameGrp + "." + att, val)
                            inConn = cmds.listConnections(
                                realAtt, s=True, d=False, c=True, scn=False
                            )
                            if inConn:
                                cmds.connectAttr(inConn[0], theFrameGrp + "." + att)

                # restoreVals
                for attr, val in storedStates.items():
                    cmds.setAttr(attr, val)

        return createdShapes

    def restoreBackUp(self, forceTransform=True):
        theBlurNode = self.currentBlurNode

        geos, geoIndices = self.getGeom(theBlurNode, transform=True)

        selectedGeometries = [
            el
            for el in cmds.ls(sl=True, tr=True, l=True)
            if cmds.listRelatives(el, type="mesh")
        ]
        if not selectedGeometries:
            cmds.confirmDialog(t="Fail", m="select geometries to restore")
            return

        dicVal = {"blurNode": theBlurNode}

        posesIndices = cmds.getAttr(theBlurNode + ".poses", mi=True)
        if posesIndices:
            posesIndices = list(map(int, posesIndices))
            poseNames = [
                cmds.getAttr("{blurNode}.poses[{i}].poseName".format(i=i, **dicVal))
                for i in posesIndices
            ]
        else:
            posesIndices = []
            poseNames = [
                cmds.getAttr("{blurNode}.poses[{i}].poseName".format(i=i, **dicVal))
                for i in posesIndices
            ]

        toRestore = {}

        for geom in selectedGeometries:
            (prt,) = cmds.listRelatives(geom, parent=True, path=True) or [None]
            if prt:
                (grp,) = cmds.listRelatives(prt, parent=True, path=True) or [None]
            else:
                grp = None

            geomlongSplitted = geom.split("|")[-1]
            split = geomlongSplitted.split("_")
            poseName = split[1]
            frame = split[2]

            deformedGeometry = "_".join(split[3:]) if len(split) > 3 else ""
            if deformedGeometry not in geos:
                deformedGeometry = geos[0]

            frame = float(frame[1:])

            if cmds.attributeQuery("sourceMesh", node=geom, ex=True):
                sourceMesh = cmds.getAttr(geom + ".sourceMesh")
                if cmds.objExists(sourceMesh):
                    deformedGeometry = sourceMesh

            if poseName not in poseNames:
                local = True
                poseTransform = ""
                if prt and cmds.attributeQuery("deformationType", node=prt, ex=True):
                    local = cmds.getAttr(prt + ".deformationType") == 0

                self.addNewPose(
                    poseName,
                    local=local,
                    poseTransform=poseTransform,
                    withRefresh=False,
                )

                posesIndices = list(
                    map(int, cmds.getAttr(theBlurNode + ".poses", mi=True))
                )
                poseNames = [
                    cmds.getAttr("{blurNode}.poses[{i}].poseName".format(i=i, **dicVal))
                    for i in posesIndices
                ]
                dicVal["indPose"] = posesIndices[poseNames.index(poseName)]

                # store attributes
                for parentNode in [prt, grp]:
                    if not parentNode:
                        continue

                    if cmds.attributeQuery("poseMatrix", node=parentNode, ex=True):
                        poseMatrixConn = cmds.getAttr(parentNode + ".poseMatrix")
                        if cmds.objExists(poseMatrixConn):
                            try:
                                cmds.connectAttr(
                                    poseMatrixConn,
                                    "{blurNode}.poses[{indPose}].poseMatrix".format(
                                        **dicVal
                                    ),
                                    f=True,
                                )
                            except Exception:
                                pass

                    for att in ["poseGain", "poseOffset", "poseEnabled"]:
                        if cmds.attributeQuery(att, node=parentNode, ex=True):
                            dicVal["att"] = att
                            toRestore[
                                "{blurNode}.poses[{indPose}].{att}".format(**dicVal)
                            ] = (parentNode + "." + att)
            else:
                dicVal["indPose"] = posesIndices[poseNames.index(poseName)]

            cmds.currentTime(frame)
            if forceTransform:
                newGeomName = cmds.parent(geom, deformedGeometry)
                cmds.makeIdentity(
                    newGeomName,
                    apply=True,
                    translate=True,
                    rotate=True,
                    scale=True,
                    normal=0,
                    preserveNormals=False,
                )
                if prt:
                    (geom,) = cmds.parent(newGeomName, prt)

            # add the pose
            cmds.blurSculpt(
                deformedGeometry,
                blurSculptName=theBlurNode,
                addAtTime=geom,
                poseName=poseName,
                offset=self.offset,
            )
            # find the index of frame
            rootAtt = "{blurNode}.poses[{indPose}].deformations".format(**dicVal)
            allFrames = {
                cmds.getAttr("{}[{}].frame".format(rootAtt, indexFrame)): indexFrame
                for indexFrame in cmds.getAttr(rootAtt, mi=True)
            }
            dicVal["frameInd"] = allFrames[frame]
            # store attributes
            for parentNode in [prt, geom]:
                if not parentNode:
                    continue
                for att in ["gain", "offset", "frameEnabled"]:
                    if cmds.attributeQuery(att, node=parentNode, ex=True):
                        dicVal["att"] = att
                        toRestore[
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].{att}".format(
                                **dicVal
                            )
                        ] = (parentNode + "." + att)

        # restore attributes
        for attDest, attSrc in toRestore.items():
            val = cmds.getAttr(attSrc)
            cmds.setAttr(attDest, val)
            inConn = cmds.listConnections(attSrc, s=True, d=False, c=True, scn=False)
            if inConn:
                cmds.connectAttr(inConn[0], attDest, f=True)

        cmds.evalDeferred(self.refresh)

    def doKeepShapes(self):
        self.keepShapes = self.popup_option.actions()[0].isChecked()
        intVal = 1 if self.keepShapes else 0
        cmds.optionVar(intValue=("blurScluptKeep", intVal))

    def on_context_menu(self, event):
        pos = event.pos()
        globalPos = event.globalPos()
        self.clickedItem = self.uiFramesTW.itemAt(pos)
        self.popup_menu.fromFrame = False
        nbSelectedFrames = len(self.uiFramesTW.selectedItems())
        self.launchPopupMenu(globalPos, nbSelectedFrames)

    def launchPopupMenu(self, posi, nbSelectedFrames=1):
        self.applyScriptJob = False
        self.popup_menu.multiSelection = nbSelectedFrames > 1
        self.popup_menu.somethingSelected = nbSelectedFrames > 0

        for i in range(0, 8):
            self.popup_menu.actions()[i].setVisible(not self.popup_menu.multiSelection)
        for i in range(10, 13):
            self.popup_menu.actions()[i].setVisible(not self.popup_menu.fromFrame)
        # paste deltas
        for i in range(0, 14):
            self.popup_menu.actions()[i].setEnabled(self.popup_menu.somethingSelected)

        self.popup_menu.actions()[-6].setEnabled(self.copiedFrame != "")
        self.popup_menu.exec_(posi)

    def jumpToFrame(self):
        if not self.clickedItem:
            return
        frameIndex = float(self.clickedItem.text(0))
        cmds.currentTime(frameIndex)

    def selectVertices(self):
        frameChannel = str(self.clickedItem.data(0, QtCore.Qt.UserRole))
        toSelect = []
        storedVectorsIndices = (
            cmds.getAttr(frameChannel + ".storedVectors", mi=True) or []
        )

        indicesMeshes = sorted(
            zip(self.currentGeometriesIndices, self.currentGeometries)
        )
        indexToMesh = {}
        for ind, msh in indicesMeshes:
            indexToMesh[ind] = msh
        toHilite=[]
        for ind in storedVectorsIndices:
            if ind in indexToMesh:
                vertices = cmds.getAttr(
                    frameChannel
                    + ".storedVectors[{}].multiVectorMovements".format(ind),
                    mi=True,
                )
                if vertices:
                    toSelect += [
                        "{}.vtx[{}]".format(indexToMesh[ind], el)
                        for el in orderMelList(vertices)
                    ]
                    toHilite.append(indexToMesh[ind])

        if toSelect:
            with extraWidgets.WaitCursorCtxt():
                cmds.select(toSelect)
                cmds.hilite(toHilite)
        else:
            cmds.select(clear=True)

    # ------------------- EXTERNAL CALL
    def callAddPose(self):
        self.toRestore = []
        for el in self.__dict__.values():
            try:
                if self.isEnabled():
                    el.setEnabled(False)
                    self.toRestore.append(el)
            except Exception:
                continue

        self.addPoseWin = utils.launchDialog(
            self,
            blurAddPose.BlurAddPose,
            self.addPoseWin,
            modal=False,
            instanced=True,
        )
        #self.addPoseWin.refreshWindow()

    def callSaveXml(self):
        self.toRestore = []
        for el in self.__dict__.values():
            try:
                if self.isEnabled():
                    el.setEnabled(False)
                    self.toRestore.append(el)
            except Exception:
                continue

        self.saveXmlWin = utils.launchDialog(
            self,
            storeXml.StoreXml,
            self.saveXmlWin,
            modal=False,
            instanced=True,
        )

        self.saveXmlWin.setEnabled(True)
        self.saveXmlWin.setUpFilePicker(store=True)
        if self.uiBlurNodesTW.multiSelection:
            selectedItems = [el.text(0) for el in self.uiBlurNodesTW.selectedItems()]
            self.saveXmlWin.refreshTree(selectedItems)
        else:
            self.saveXmlWin.refreshTree(self.currentBlurNode)

    def callOpenXml(self):
        self.toRestore = []
        for el in self.__dict__.values():
            try:
                if self.isEnabled():
                    el.setEnabled(False)
                    self.toRestore.append(el)
            except Exception:
                continue

        self.saveXmlWin = utils.launchDialog(
            self,
            storeXml.StoreXml,
            self.saveXmlWin,
            modal=False,
            instanced=True,
        )

        self.saveXmlWin.setEnabled(True)
        self.saveXmlWin.setUpFilePicker(store=False)

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(BlurDeformDialog, self).__init__(parent)

        self.addTimeLine = True
        self.applyScriptJob = True

        self.currentBlurNode = ""
        self.currentGeom = ""
        self.currentGeometries = []
        self.currentGeometriesIndices = []
        self.currentPose = ""
        self.copiedFrame = ""

        self.addPoseWin = None
        self.blurDeformQueryMeshesWin = None
        self.saveXmlWin = None

        mel.eval("makePaintable -attrType multiFloat -sm deformer blurSculpt weights")

        self.offset = 0.001
        if cmds.optionVar(exists="blurScluptOffset"):
            self.offset = cmds.optionVar(q="blurScluptOffset")

        # load the ui
        QtCompat.loadUi(utils.getUiFile(__file__), self)
        self._setButtonIcons()

        self.progressBar.hide()
        self.blueCol = QtGui.QColor(50, 50, 100)

        self.uiDisconnectMatrixBTN.setIcon(utils.ICONS["disconnect"])
        self.uiDisconnectMatrixBTN.setText("")

        self.uiRefreshBTN.setIcon(utils.ICONS["refresh"])
        self.uiRefreshBTN.setText("")
        self.uiFromSelectionBTN.setIcon(utils.ICONS["fromScene"])
        self.uiFromSelectionBTN.setText("")
        self.uiEmptyFrameBTN.setIcon(utils.ICONS["empty"])
        self.uiEmptyFrameBTN.setText("")

        self.uiEditModeBTN.setIcon(utils.ICONS["edit"])
        self.uiExitEditModeBTN.setIcon(utils.ICONS["cancelEdit"])

        self.uiOptionsBTN.setIcon(utils.ICONS["gear"])
        self.uiOptionsBTN.setText("")

        self.uiFramesTW.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.create_popup_menu()
        self.uiFramesTW.contextMenuEvent = self.on_context_menu

        self.uiPoseGB.toggled.connect(self.resizePoseInfo)
        self.uiRefreshBTN.clicked.connect(self.refresh)
        self.uiFromSelectionBTN.clicked.connect(self.selectFromScene)
        self.uiEmptyFrameBTN.clicked.connect(self.addEmptyFrame)

        # - delete
        self.uiDeleteBlurNodeBTN.clicked.connect(self.delete_sculpt)
        self.uiRmvMeshToBlurNodeBTN.clicked.connect(self.rmvMeshFromDeformer)
        self.uiDeleteFrameBTN.clicked.connect(self.delete_frame)
        self.uiDeletePoseBTN.clicked.connect(self.delete_pose)
        # - Add
        self.uiAddBlurNodeBTN.clicked.connect(self.addDeformer)
        self.uiAddMeshToBlurNodeBTN.clicked.connect(self.addMeshToDeformer)
        self.uiAddFrameBTN.clicked.connect(self.addNewFrame)
        self.uiAddPoseBTN.clicked.connect(self.callAddPose)
        self.uiEditModeBTN.clicked.connect(self.enterEditMode)
        self.uiExitEditModeBTN.clicked.connect(self.exitEditMode)

        self.uiPickTransformBTN.clicked.connect(self.connectMatrix)
        self.uiDisconnectMatrixBTN.clicked.connect(self.disConnectMatrix)

        self.uiBlurNodesTW.itemDoubleClicked.connect(self.doubleClickChannel)

        # time slider part
        if self.addTimeLine:
            self.blurTimeSlider = extraWidgets.TheTimeSlider(self)
            self.layout().addWidget(self.blurTimeSlider)
        self.uiPoseGB.setChecked(False)

        self.uiPosesTW.currentItemChanged.connect(self.refreshPoseInfo)
        self.uiPosesTW.itemChanged.connect(self.renamePose)

        self.uiBlurNodesTW.multiSelection = False
        self.uiBlurNodesTW.mousePressEvent = self.uiBlurNodesTWMPE
        self.uiBlurNodesTW.itemClicked.connect(self.changedSelection)

        self.uiFramesTW.itemChanged.connect(self.changeTheFrame)
        self.uiFramesTW.itemSelectionChanged.connect(self.selectFrameInTimeLine)

        self.uiFramesTW.mousePressEvent = self.uiFramesTWMPE

        self.uiEnvelopeWg = extraWidgets.SpinnerWidget("", singleStep=1.0, precision=1)
        self.uiEnvelopeWg.setParent(self.label)
        self.uiEnvelopeWg.move(50, 0)
        self.uiEnvelopeWg.resize(50, 25)

    def _setButtonIcons(self):
        """Set the icons for some buttons"""
        for nameBtn in ["PoseBTN", "FrameBTN", "BlurNodeBTN"]:
            for nm in ["Add", "Delete"]:
                btn = self.__dict__["ui{0}{1}".format(nm, nameBtn)]
                btn.setIcon(utils.ICONS[nm])
                if (nameBtn, nm) == ("FrameBTN", "Add"):
                    btn.setIcon(utils.ICONS["addFrame"])
                btn.setText("")

        for nameBtn in ["AddMeshToBlurNode", "RmvMeshToBlurNode"]:
            btn = self.__dict__["ui{}BTN".format(nameBtn)]
            btn.setIcon(utils.ICONS[nameBtn])
            btn.setText("")

        for nm in ["BlurNodes", "Frames", "Poses"]:
            self.__dict__["ui" + nm + "TW"].setRootIsDecorated(False)

    def uiFramesTWMPE(self, event):
        if event.button() == QtCore.Qt.MidButton:
            pos = event.pos()
            self.clickedItem = self.uiFramesTW.itemAt(pos)
            self.jumpToFrame()
        QtWidgets.QTreeWidget.mousePressEvent(self.uiFramesTW, event)

    def uiBlurNodesTWMPE(self, *args):
        shiftPressed = args[0].modifiers() == QtCore.Qt.ShiftModifier
        ctrlPressed = shiftPressed or (args[0].modifiers() == QtCore.Qt.ControlModifier)

        if ctrlPressed:
            if shiftPressed:
                self.uiBlurNodesTW.setSelectionMode(3)
            else:
                self.uiBlurNodesTW.setSelectionMode(
                    2
                )  # QtWidgets.QAbstractView.MultiSelection)
            with extraWidgets.toggleBlockSignals(
                [self.uiBlurNodesTW, self.uiPosesTW, self.uiFramesTW]
            ):
                self.uiPosesTW.clear()
                self.uiFramesTW.clear()
        else:
            self.uiBlurNodesTW.setSelectionMode(1)
        self.uiBlurNodesTW.multiSelection = ctrlPressed
        QtWidgets.QTreeWidget.mousePressEvent(self.uiBlurNodesTW, *args)

    def selectProximityKey(self):
        if self.applyScriptJob:
            currTime = cmds.currentTime(q=True)
            self.selectFrameTime(currTime)
        else:
            self.applyScriptJob = True

    def addtheCallBack(self):
        self.playBackScript = cmds.scriptJob(
            e=["playbackRangeChanged", self.blurTimeSlider.updateKeys],
            protected=True,
        )
        self.timeSliderChange = cmds.scriptJob(
            e=["timeChanged", self.selectProximityKey], protected=True
        )

    def deleteScriptJob(self):
        cmds.scriptJob(kill=self.playBackScript, force=True)
        cmds.scriptJob(kill=self.timeSliderChange, force=True)

    def refreshForShow(self):
        if not cmds.pluginInfo("blurPostDeform", q=True, loaded=True):
            cmds.loadPlugin("blurPostDeform")

        if self.addTimeLine:
            self.addtheCallBack()
            self.blurTimeSlider.deleteKeys()

        self.currentBlurNode = ""
        self.currentGeom = ""
        self.currentPose = ""
        self.resForDuplicate = []

        cmds.evalDeferred(self.refresh)

    def showEvent(self, event):
        self.refreshForShow()
        super(BlurDeformDialog, self).showEvent(event)

    def closeEvent(self, event):
        if self.addTimeLine:
            self.deleteScriptJob()
        super(BlurDeformDialog, self).closeEvent(event)
