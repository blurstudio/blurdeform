from __future__ import print_function
from __future__ import absolute_import
from Qt import QtCore, QtWidgets, QtCompat
import difflib
from maya import cmds
from six.moves import range
from six.moves import zip
from .utils import getUiFile

try:
    # Blur adds some extra signal handling to the top-level dialogs
    from blurdev.gui import Dialog
except ImportError:
    Dialog = QtWidgets.QDialog


class BlurDeformQueryMeshes(Dialog):
    def __init__(self, parent=None, lstMeshes=None, listToSelect=None, addComboMeshes=None):
        super(BlurDeformQueryMeshes, self).__init__(parent)
        self.btnClicked = None
        self.listSelectedMeshes = []

        # load the ui
        self.parentWindow = parent
        QtCompat.loadUi(getUiFile(__file__), self)

        self.buttonBox.clicked.connect(self.infoClick)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Yes).setText("Add Selected")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.YesToAll).setText("Add All")

        # self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        #self.setWindowModality
        self.setWindowTitle("Pick meshes to Add")

        self.addComboMeshes = None
        self.refreshWindow(lstMeshes, listToSelect, addComboMeshes)

    def closeEvent(self, event):
        self.listSelectedMeshes = []  # same as rejected
        super(BlurDeformQueryMeshes, self).closeEvent(event)

    def refreshWindow(self, lstMeshes, listToSelect, addComboMeshes):
        self.addComboMeshes = addComboMeshes

        nbVtxOrig = []
        if self.addComboMeshes:
            self.uiMeshesLW.setHeaderHidden(False)
            self.uiMeshesLW.setColumnCount(2)
            self.uiMeshesLW.setHeaderLabels(["selection", "deformedMeshes"])
            nbVtxOrig = [cmds.polyEvaluate(el, v=True) for el in self.addComboMeshes]
            origName_nbOrigVtx = list(zip(self.addComboMeshes, nbVtxOrig))

        else:
            self.uiMeshesLW.setHeaderHidden(True)
            self.uiMeshesLW.setColumnCount(1)
            origName_nbOrigVtx = []

        self.listSelectedMeshes = []
        self.uiMeshesLW.clear()
        for ind, nm in enumerate(lstMeshes):
            print(nm)
            item = QtWidgets.QTreeWidgetItem(self.uiMeshesLW)
            item.setText(0, nm)
            item.setFlags(
                item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            )
            # self.uiMeshesLW.addTopLevelItem(item)

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
            QtWidgets.QDialogButtonBox.StandardButton.YesToAll
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

        super(BlurDeformQueryMeshes, self).accept()

    def reject(self):
        self.listSelectedMeshes = []
        super(BlurDeformQueryMeshes, self).accept()
