from blurdev.gui import Dialog
from studio.gui.resource import Icons
from Qt import QtCore, QtGui, QtWidgets
import blurdev

from maya import cmds, mel

from functools import partial


class blurDeformQueryMeshes(Dialog):
    listSelectedMeshes = []

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
        else:
            self.uiMeshesLW.setHeaderHidden(True)
            self.uiMeshesLW.setColumnCount(1)

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
                if nbVtx in nbVtxOrig:
                    ind = nbVtxOrig.index(nbVtx)
                    cb.setCurrentIndex(ind)
                    item.setSelected(True)

            elif nm in listToSelect:
                item.setSelected(True)

    def accept(self):
        if self.addComboMeshes:
            self.listSelectedMeshes = [
                (item.text(0), self.uiMeshesLW.itemWidget(item, 1).currentText())
                for item in self.uiMeshesLW.selectedItems()
            ]
        else:
            self.listSelectedMeshes = [
                item.text(0) for item in self.uiMeshesLW.selectedItems()
            ]
        # print "ACCEPTED"
        super(blurDeformQueryMeshes, self).accept()

    def reject(self):
        # print "REJECTED"
        self.listSelectedMeshes = []
        super(blurDeformQueryMeshes, self).accept()

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(blurDeformQueryMeshes, self).__init__(parent)
        # load the ui
        import __main__

        self.parentWindow = __main__.__dict__["blurDeformWindow"]
        self.parentWindow.blurDeformQueryMeshesWin = self
        blurdev.gui.loadUi(__file__, self)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Pick meshes to Add")
        # self.setModal (True)
        lstMeshes, listToSelect, self.addComboMeshes = self.parentWindow.argsQueryMeshes
        self.refreshWindow(lstMeshes, listToSelect)
