from __future__ import print_function
from blurdev.gui import Dialog
from studio.gui.resource import Icons
from Qt import QtCore, QtGui, QtWidgets
import blurdev
import difflib
from maya import cmds, mel

from functools import partial


class blurDeformQueryMeshes(Dialog):

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(blurDeformQueryMeshes, self).__init__(parent)
        self.btnClicked = None
        self.listSelectedMeshes = []

        # load the ui
        import __main__

        self.parentWindow = __main__.__dict__["blurDeformWindow"]
        self.parentWindow.blurDeformQueryMeshesWin = self
        blurdev.gui.loadUi(__file__, self)

        self.buttonBox.clicked.connect(self.infoClick)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setText("Add Selected")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.YesToAll).setText("Add All")

        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Pick meshes to Add")
        # self.setModal (True)
        lstMeshes, listToSelect, self.addComboMeshes = self.parentWindow.argsQueryMeshes
        self.refreshWindow(lstMeshes, listToSelect)

    def closeEvent(self, event):
        self.listSelectedMeshes = []  # same as rejected
        super(blurDeformQueryMeshes, self).closeEvent(event)

    def refreshWindow(self, lstMeshes, listToSelect):
        nbVtxOrig = []
        if self.addComboMeshes:
            self.uiMeshesLW.setHeaderHidden(False)
            self.uiMeshesLW.setColumnCount(2)
            self.uiMeshesLW.setHeaderLabels(["selection", "deformedMeshes"])
            nbVtxOrig = [cmds.polyEvaluate(el, v=True) for el in self.addComboMeshes]
            origName_nbOrigVtx = zip(self.addComboMeshes, nbVtxOrig)

        else:
            self.uiMeshesLW.setHeaderHidden(True)
            self.uiMeshesLW.setColumnCount(1)
            origName_nbOrigVtx = []

        # print lstMeshes, listToSelect
        self.listSelectedMeshes = []
        self.uiMeshesLW.clear()
        for ind, nm in enumerate(lstMeshes):
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, nm)
            item.setFlags(
                item.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable
            )
            self.uiMeshesLW.addTopLevelItem(item)

            if self.addComboMeshes:
                cb = QtWidgets.QComboBox(self)
                cb.addItems(self.addComboMeshes)
                self.uiMeshesLW.setItemWidget(item, 1, cb)

                nbVtx = cmds.polyEvaluate(nm, v=True)
                lstOrigNm = [
                    origName
                    for origName, nbOrigVtx in origName_nbOrigVtx
                    if nbVtx == nbOrigVtx
                ]
                ind = -1
                if len(lstOrigNm) > 1:
                    matchNames = difflib.get_close_matches(nm, lstOrigNm, 1, 0.2) or []
                    if matchNames:
                        ind = self.addComboMeshes.index(matchNames[0])
                    else:
                        print("matchName problem ", nm, lstOrigNm)

                elif len(lstOrigNm) == 1:
                    ind = nbVtxOrig.index(nbVtx)
                cb.setCurrentIndex(ind)
                if ind != -1:
                    item.setSelected(True)

            elif nm in listToSelect:
                item.setSelected(True)

    def infoClick(self, btn):
        self.btnClicked = btn

    def accept(self):
        addAll = self.btnClicked is self.buttonBox.button(
            QtWidgets.QDialogButtonBox.YesToAll
        )

        topItems = (
            [
                self.uiMeshesLW.topLevelItem(i)
                for i in range(self.uiMeshesLW.topLevelItemCount())
            ]
            if addAll
            else []
        )

        if self.addComboMeshes:
            if addAll:
                self.listSelectedMeshes = [
                    (item.text(0), self.uiMeshesLW.itemWidget(item, 1).currentText())
                    for item in topItems
                ]
            else:
                self.listSelectedMeshes = [
                    (item.text(0), self.uiMeshesLW.itemWidget(item, 1).currentText())
                    for item in self.uiMeshesLW.selectedItems()
                ]
        else:
            if addAll:
                self.listSelectedMeshes = [item.text(0) for item in topItems]
            else:
                self.listSelectedMeshes = [
                    item.text(0) for item in self.uiMeshesLW.selectedItems()
                ]
        # print "ACCEPTED ", self.result()

        super(blurDeformQueryMeshes, self).accept()

    def reject(self):
        # print "REJECTED"
        self.listSelectedMeshes = []
        super(blurDeformQueryMeshes, self).accept()
