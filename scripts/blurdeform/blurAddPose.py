from blurdev.gui import Dialog
from studio.gui.resource import Icons
from Qt import QtCore
import blurdev.debug


import blurdev

from maya import cmds, mel
import sip


class BlurAddPose(Dialog):
    def closeEvent(self, event):
        for el in self.parentWindow.toRestore:
            el.setEnabled(True)
        super(BlurAddPose, self).closeEvent(event)

    def addNewPose(self):
        newName = str(self.uiPoseNameLE.text())
        if not self.parentWindow.isValidName(newName):
            self.uiWarningExistPoseNameLabel.show()
            self.uiPoseNameLE.selectAll()
        else:
            self.parentWindow.addNewPose(
                newName,
                local=self.uiLocalDeformationRB.isChecked(),
                poseTransform=str(self.uiTransformLE.text()),
            )
            self.close()

    def getSelectedTransform(self):
        selection = cmds.ls(sl=True, tr=True)
        if selection:
            self.uiTransformLE.setText(selection[0])

    def refreshWindow(self):
        self.uiWarningExistPoseNameLabel.hide()
        parentWindGeom = self.parentWindow.geometry()
        currentGeom = self.geometry()
        XPos = parentWindGeom.x() + 0.5 * (parentWindGeom.width() - currentGeom.width())
        YPos = parentWindGeom.y() + 0.5 * (
            parentWindGeom.height() - currentGeom.height()
        )
        self.move(XPos, YPos)
        self.setEnabled(True)
        self.activateWindow()
        self.uiPoseNameLE.setFocus()
        self.uiTransformLE.setText("N/A")
        self.uiPoseNameLE.selectAll()

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(BlurAddPose, self).__init__(parent)
        # load the ui

        import __main__

        self.parentWindow = __main__.__dict__["blurDeformWindow"]
        self.parentWindow.addPoseWin = self
        blurdev.gui.loadUi(__file__, self)

        self.uiTransformLE.setText("N/A")
        self.uiPoseNameLE.setText("newPose")

        self.uiAddPoseBTN.clicked.connect(self.addNewPose)
        self.uiPickTransformBTN.clicked.connect(self.getSelectedTransform)

        self.uiLocalDeformationRB.toggled.connect(self.uiTransformLE.setEnabled)
        self.uiLocalDeformationRB.toggled.connect(self.uiPickTransformBTN.setEnabled)
        self.uiLocalDeformationRB.toggled.connect(self.uiUseTransformLBL.setEnabled)
        self.uiTangentDeformationRB.toggled.connect(self.uiWarningLabel.setVisible)
        self.uiWarningLabel.setVisible(False)
        self.uiWarningExistPoseNameLabel.hide()

        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Add New Pose")
