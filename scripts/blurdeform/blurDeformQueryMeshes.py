from __future__ import print_function
from blurdev.gui import Dialog
from studio.gui.resource import Icons
from Qt import QtCore
import blurdev.debug


import blurdev

from maya import cmds, mel
import sip


class blurDeformQueryMeshes(Dialog):
    listSelectedMeshes = []

    def closeEvent(self, event):
        self.listSelectedMeshes = []  # same as rejected
        super(blurDeformQueryMeshes, self).closeEvent(event)

    """
    def showEvent (self, event):
        print "SHOWING"
        super(blurDeformQueryMeshes, self).showEvent(event)
    """

    def refreshWindow(self, lstMeshes, listToSelect):
        # print lstMeshes, listToSelect
        self.listSelectedMeshes = []
        self.uiMeshesLW.clear()
        for ind, nm in enumerate(lstMeshes):
            self.uiMeshesLW.addItem(nm)
            item = self.uiMeshesLW.item(ind)
            if nm in listToSelect:
                item.setSelected(True)

    def accept(self):
        self.listSelectedMeshes = [
            item.text() for item in self.uiMeshesLW.selectedItems()
        ]
        # print "ACCEPTED"
        super(blurDeformQueryMeshes, self).accept()

    def reject(self):
        # print "REJECTED"
        self.listSelectedMeshes = []
        super(blurDeformQueryMeshes, self).accept()

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        print("INIT")
        super(blurDeformQueryMeshes, self).__init__(parent)
        # load the ui
        import __main__

        self.parentWindow = __main__.__dict__["blurDeformWindow"]
        self.parentWindow.blurDeformQueryMeshesWin = self
        blurdev.gui.loadUi(__file__, self)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Pick meshes to Add")
        # self.setModal (True)

        self.refreshWindow(*self.parentWindow.argsQueryMeshes)
