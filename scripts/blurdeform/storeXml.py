from __future__ import print_function
from __future__ import absolute_import

import os
import re
import codecs

from maya import cmds
from xml.dom import minidom
from xml.etree import ElementTree

from . import extraWidgets, filepickerwidget, utils
from .Qt import QtGui, QtWidgets, QtCore, QtCompat

import six
from six.moves import range, map, zip


class StoreXml(QtWidgets.QDialog):
    def closeEvent(self, event):
        for el in self.parentWindow.toRestore:
            el.setEnabled(True)
        super(StoreXml, self).closeEvent(event)

    def setUpFilePicker(self, store=True):
        # prepare the file picker
        with extraWidgets.toggleBlockSignals([self.uiXmlStoreFile]):
            self.uiXmlStoreFile.setFilePath("")

        sceneName = cmds.file(q=True, sceneName=True)
        splt = sceneName.split("/")
        startDir = "/".join(splt[:-1])
        self.uiXmlStoreFile._defaultLocation = startDir

        if store:
            self.storewin = True
            self.uiDoStoreBTN.setText("store xml")
            self.uiXmlStoreFile.pyOpenFile = False
            self.uiXmlStoreFile.pyCaption = "Store xml..."
            self.uiDoStoreBTN.setEnabled(False)
            self.setWindowTitle("Store xml file")

        else:
            self.storewin = False
            self.uiDoStoreBTN.setText("restore selected frames")
            self.uiXmlStoreFile.pyOpenFile = True
            self.uiXmlStoreFile.pyCaption = "select file to load from..."
            self.uiDoStoreBTN.setEnabled(True)
            self.setWindowTitle("Restore from xml file")

        self.uiAllFramesTW.setEnabled(self.storewin)
        self.uiAllFramesTW.clear()
        self.uiAllFramesTW.setColumnCount(4)
        self.uiAllFramesTW.setHeaderLabels(
            ["blurSculpt", "mesh", "pose", "frame", "isEmpty"]
        )
        self.setTreePretty()

    def refreshTree(self, blurNodes):
        # fill the tree of frames
        if not isinstance(blurNodes, list):
            blurNodes = [blurNodes]
        for blurNode in blurNodes:
            dicVal = {"blurNode": blurNode}
            posesIndices = list(map(int, cmds.getAttr(blurNode + ".poses", mi=True)))

            theParent = self.parentWindow.getGeom(blurNode, transform=True)

            # first store positions
            for logicalInd in posesIndices:
                dicVal["indPose"] = logicalInd

                thePose = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].poseName".format(**dicVal)
                )
                listDeformationsIndices = cmds.getAttr(
                    "{blurNode}.poses[{indPose}].deformations".format(**dicVal),
                    mi=True,
                )
                if not listDeformationsIndices:
                    continue

                toAdd = []
                for logicalFrameIndex in listDeformationsIndices:
                    dicVal["frameInd"] = logicalFrameIndex
                    frame = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                            **dicVal
                        )
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
                    vectorMovementsIndices = []
                    for ind in storedVectorsIndices:
                        dicVal["geoIndex"] = ind
                        vectorMovementsIndices = cmds.getAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors[{geoIndex}].multiVectorMovements".format(
                                **dicVal
                            ),
                            mi=True,
                        )
                        if vectorMovementsIndices:
                            break

                    frameItem = QtWidgets.QTreeWidgetItem()
                    frameItem.setText(0, str(blurNode))
                    frameItem.setText(1, str(theParent))
                    frameItem.setText(2, str(thePose))
                    frameItem.setText(3, str(frame))
                    if not vectorMovementsIndices:
                        frameItem.setText(4, "\u00D8")
                        frameItem.setTextAlignment(4, QtCore.Qt.AlignCenter)

                    frameItem.setData(
                        0,
                        QtCore.Qt.UserRole,
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}]".format(
                            **dicVal
                        ),
                    )
                    toAdd.append((frame, frameItem))

                for _frame, frameItem in sorted(toAdd):
                    self.uiAllFramesTW.addTopLevelItem(frameItem)
        self.setTreePretty()

    def setTreePretty(self):
        self.uiAllFramesTW.setEnabled(True)
        for i in range(5):
            self.uiAllFramesTW.resizeColumnToContents(i)
        self.uiAllFramesTW.selectAll()
        for i in range(5):
            wdt = self.uiAllFramesTW.columnWidth(i)
            self.uiAllFramesTW.setColumnWidth(i, wdt + 10)

    def buttonAction(self):
        if self.storewin:
            self.doStoreXml()
        else:
            if self.parentWindow.uiBlurNodesTW.multiSelection:
                self.doRetrieveSelectionMulti()
            else:
                self.doRetrieveSelection()
            QtCore.QTimer.singleShot(0, self.parentWindow.refresh)

        self.close()

    def doRetrieveSelectionMulti(self):
        selectedItems = self.uiAllFramesTW.selectedItems()
        dicBlurNodeData = {}
        for frameItem in selectedItems:
            frame_tag = frameItem.data(0, QtCore.Qt.UserRole)
            pose_tag = frameItem.data(1, QtCore.Qt.UserRole)
            geom = frameItem.text(1)
            if geom in self.blurDic:
                inSceneBlurNode = self.blurDic[geom]
                if inSceneBlurNode not in dicBlurNodeData:
                    dicBlurNodeData[inSceneBlurNode] = {}, []
                dicFrames, listPoses = dicBlurNodeData[inSceneBlurNode]

                poseName = pose_tag.get("poseName")
                if poseName not in dicFrames:
                    dicFrames[poseName] = [frame_tag]
                    listPoses.append(pose_tag)
                else:
                    dicFrames[poseName].append(frame_tag)

        with extraWidgets.WaitCursorCtxt():
            with extraWidgets.MayaProgressBar(
                maxValue=len(dicBlurNodeData),
                status="retrieve ...",
                QTprogress=self.progressBar,
                frontWindow=False,
            ) as pBar:
                for blurNode, (dicFrames, listPoses) in dicBlurNodeData.items():
                    if not pBar.update():
                        break
                    self.retrieveblurXml(dicFrames, listPoses, theBlurNode=blurNode)

    def doRetrieveSelection(self):
        selectedItems = self.uiAllFramesTW.selectedItems()
        dicFrames = {}
        listPoses = []
        for frameItem in selectedItems:
            frame_tag = frameItem.data(0, QtCore.Qt.UserRole)
            pose_tag = frameItem.data(1, QtCore.Qt.UserRole)

            poseName = pose_tag.get("poseName")

            if poseName not in dicFrames:
                dicFrames[poseName] = [frame_tag]
                listPoses.append(pose_tag)
            else:
                dicFrames[poseName].append(frame_tag)

        # print "do retrieve done"
        with extraWidgets.WaitCursorCtxt():
            self.retrieveblurXml(dicFrames, listPoses)

    def retrieveblurXml(self, dicFrames, listPoses, theBlurNode=None):
        # do several
        if not theBlurNode:
            theBlurNode = self.parentWindow.currentBlurNode
        dicVal = {"blurNode": theBlurNode}

        blurNodeMeshToIndex, geomSorted = self.blurInfo[theBlurNode]
        fileIndexToMesh = self.blurFileInfo[geomSorted]

        dicIndexFileToIndexNode = {}
        for indexGeo, meshName in six.iteritems(blurNodeMeshToIndex):
            indexFile = fileIndexToMesh[meshName]
            dicIndexFileToIndexNode[indexFile] = indexGeo

        pses = cmds.getAttr(theBlurNode + ".poses", mi=True)
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

        for pose_tag in listPoses:
            poseName = pose_tag.get("poseName")
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
                            "{blurNode}.poses[{indPose}].poseMatrix".format(**dicVal),
                            f=True,
                        )
                    except Exception:
                        pass
            else:
                dicVal["indPose"] = dicPoses[poseName]

        for poseName, listFrameTags in dicFrames.items():
            dicVal["indPose"] = dicPoses[poseName]
            dicFrames = {}
            newFrameInd = 0
            listDeformationsIndices = cmds.getAttr(
                "{blurNode}.poses[{indPose}].deformations".format(**dicVal),
                mi=True,
            )
            if listDeformationsIndices:
                for logicalFrameIndex in listDeformationsIndices:
                    dicVal["frameInd"] = logicalFrameIndex
                    frame = cmds.getAttr(
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format(
                            **dicVal
                        )
                    )
                    dicFrames[frame] = logicalFrameIndex
                newFrameInd = max(listDeformationsIndices) + 1

            for frame_tag in listFrameTags:
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
                    frameName = (
                        "{blurNode}.poses[{indPose}].deformations[{frameInd}]".format(
                            **dicVal
                        )
                    )
                    storedVectorsIndices = (
                        cmds.getAttr(frameName + ".storedVectors", mi=True) or []
                    )
                    for (
                        indexGeo
                    ) in storedVectorsIndices:  # remove if it's in the copy list
                        if indexGeo in list(
                            dicIndexFileToIndexNode.values()
                        ):  # if something we'll edit we remove it
                            cmds.removeMultiInstance(
                                frameName + ".storedVectors[{}]".format(indexGeo),
                                b=True,
                            )

                OLDvector_tag = frame_tag.find("vectorMovements")
                if OLDvector_tag is not None:
                    for vectag in list(iter(OLDvector_tag)):
                        index = int(vectag.get("index"))
                        dicVal["vecInd"] = index
                        value = vectag.get("value")
                        floatVal = list(map(float, value[1:-1].split(", ")))
                        # set to the index zero
                        cmds.setAttr(
                            "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors [0].multiVectorMovements[{vecInd}]".format(
                                **dicVal
                            ),
                            *floatVal
                        )

                # now find the new tags
                storedVectors_tag = frame_tag.find("storedVectors")
                if storedVectors_tag is not None:
                    for vector_tag in list(iter(storedVectors_tag)):
                        indexGeo = vector_tag.get("indexGeo")
                        blurNodeIndex = dicIndexFileToIndexNode[indexGeo]
                        dicVal["indexGeo"] = blurNodeIndex
                        for vectag in list(iter(vector_tag)):
                            index = int(vectag.get("index"))
                            dicVal["vecInd"] = index
                            value = vectag.get("value")
                            floatVal = list(map(float, value[1:-1].split(", ")))
                            # set to the index zero
                            cmds.setAttr(
                                "{blurNode}.poses[{indPose}].deformations[{frameInd}].storedVectors [{indexGeo}].multiVectorMovements[{vecInd}]".format(
                                    **dicVal
                                ),
                                *floatVal
                            )

    def doStoreXml(self):
        dicBlurPoses = {}
        selectedItems = self.uiAllFramesTW.selectedItems()
        destinationFile = str(self.uiXmlStoreFile.filePath())

        if selectedItems:
            for frameItem in selectedItems:
                fullName = str(frameItem.data(0, QtCore.Qt.UserRole))
                poseInd, frameInd = [
                    int(ind) for ind in re.findall(r"\b\d+\b", fullName)
                ]
                blurNode = fullName.split(".")[0]

                if blurNode not in dicBlurPoses:
                    dicBlurPoses[blurNode] = {}
                inputPoseFramesIndices = dicBlurPoses[blurNode]

                if poseInd not in inputPoseFramesIndices:
                    inputPoseFramesIndices[poseInd] = [frameInd]
                else:
                    inputPoseFramesIndices[poseInd].append(frameInd)

            with extraWidgets.WaitCursorCtxt():
                doc = minidom.Document()
                ALL_tag = doc.createElement("ALL")
                doc.appendChild(ALL_tag)

                with extraWidgets.MayaProgressBar(
                    maxValue=len(dicBlurPoses),
                    status="storeXml ...",
                    QTprogress=self.progressBar,
                    frontWindow=False,
                ) as pBar:
                    for blurNode, inputPoseFramesIndices in six.iteritems(dicBlurPoses):
                        if not pBar.update():
                            break
                        created_tag = self.parentWindow.storeInfoBlurSculpt(
                            doc,
                            blurNode,
                            inputPoseFramesIndices=inputPoseFramesIndices,
                        )
                        ALL_tag.appendChild(created_tag)
                with codecs.open(destinationFile, "w", "utf-8") as out:
                    doc.writexml(out, indent="\n", addindent="\t", newl="")

    def readXmlFile(self):
        selectedItems = [
            el.text(0) for el in self.parentWindow.uiBlurNodesTW.selectedItems()
        ]
        self.blurDic = {}
        self.blurInfo = {}
        self.blurFileInfo = {}
        for blurNode in selectedItems:
            geos, geoIndices = self.parentWindow.getGeom(blurNode, transform=True)
            geomSorted = " - ".join(sorted(geos))

            indicesMeshes = sorted(zip(geos, geoIndices))
            blurNodeMeshToIndex = {}
            for ind, msh in indicesMeshes:
                blurNodeMeshToIndex[msh] = ind
            self.blurDic[geomSorted] = blurNode
            self.blurInfo[blurNode] = (blurNodeMeshToIndex, geomSorted)

        with extraWidgets.WaitCursorCtxt():
            if os.path.isfile(self.sourceFile):
                tree = ElementTree.parse(self.sourceFile)
                root = tree.getroot()
                self.refreshTreeFromRoot(root)

    def refreshTreeFromRoot(self, root):
        chds = list(iter(root))
        geomsSelected = list(self.blurDic.keys())
        itemsToSelect = []
        with extraWidgets.MayaProgressBar(
            maxValue=len(chds),
            status="refresh ...",
            QTprogress=self.progressBar,
            frontWindow=False,
        ) as pBar:
            for ind, blurNode_tag in enumerate(chds):
                if not pBar.update():
                    break

                self.progressBar.setValue(ind)
                blurName = blurNode_tag.get("name")

                geom = blurNode_tag.get("geom")
                geomSplt = geom.split(" - ")
                geomSorted = " - ".join(sorted(geomSplt))

                if "geomIndices" in blurNode_tag.attrib:
                    geomIndices = blurNode_tag.get("geomIndices")
                    geoIndices = geomIndices.split(" - ")
                else:
                    geoIndices = ["0"]
                indicesMeshes = sorted(zip(geomSplt, geoIndices))

                blurNodeIndexToMesh = {}
                for ind, msh in indicesMeshes:
                    blurNodeIndexToMesh[ind] = msh
                self.blurFileInfo[geomSorted] = blurNodeIndexToMesh
                # multi deal - with name END

                isGeomSelected = geomSorted in geomsSelected
                for pose_tag in list(iter(blurNode_tag)):
                    poseName = pose_tag.get("poseName")
                    toAdd = []
                    for frame_tag in list(iter(pose_tag)):
                        frame = float(frame_tag.get("frame"))
                        vector_tag = list(iter(frame_tag))[0]

                        frameItem = QtWidgets.QTreeWidgetItem()

                        frameItem.setText(0, str(blurName))
                        frameItem.setText(1, str(geom))

                        if isGeomSelected:
                            frameItem.setForeground(1, QtGui.QBrush(self.yellowCol))
                            itemsToSelect.append(frameItem)
                        else:
                            frameItem.setForeground(1, QtGui.QBrush(self.redCol))

                        frameItem.setText(2, str(poseName))
                        frameItem.setText(3, str(frame))
                        if not list(iter(vector_tag)):
                            frameItem.setText(4, "\u00D8")

                        toAdd.append(("{0}_{1}".format(geom, frame), frameItem))

                        frameItem.setData(0, QtCore.Qt.UserRole, frame_tag)
                        frameItem.setData(1, QtCore.Qt.UserRole, pose_tag)

                    for _geom_frame, frameItem in sorted(toAdd):
                        self.uiAllFramesTW.addTopLevelItem(frameItem)

        self.setTreePretty()
        # doThe selection
        self.uiAllFramesTW.clearSelection()
        for widget_item in itemsToSelect:
            widget_item.setSelected(True)

    def fileIsPicked(self):
        if not self.storewin:
            self.sourceFile = str(self.uiXmlStoreFile.filePath())
            self.readXmlFile()
        else:
            self.uiDoStoreBTN.setEnabled(True)

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(StoreXml, self).__init__(parent)
        self.storewin = True

        # load the UI
        self.parentWindow = parent
        QtCompat.loadUi(utils.getUiFile(__file__), self)

        self.uiXmlStoreFile = filepickerwidget.FilePickerWidget(self)
        self.uiXmlStoreFile.setCaption("Store xml...")
        self.uiXmlStoreFile.setFilters("XML Files (*.xml)")
        self.uiStoreLAY.insertWidget(0, self.uiXmlStoreFile, 2)

        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Store xml file")
        self.uiAllFramesTW.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.uiAllFramesTW.setAlternatingRowColors(True)

        self.uiDoStoreBTN.clicked.connect(self.buttonAction)

        self.uiXmlStoreFile.filenameChanged.connect(self.fileIsPicked)
        self.progressBar.hide()

        self.yellowCol = QtGui.QColor(250, 250, 100)
        self.redCol = QtGui.QColor(250, 100, 100)
