from __future__ import absolute_import
from Qt import QtCore, QtWidgets, QtCompat
from maya import cmds
from .utils import getUiFile

try:
    # Blur adds some extra signal handling to the top-level dialogs
    from blurdev.gui import Dialog
except ImportError:
    Dialog = QtWidgets.QDialog


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
        self.move(int(XPos), int(YPos))
        self.setEnabled(True)
        self.activateWindow()
        self.uiPoseNameLE.setFocus()
        self.uiTransformLE.setText("N/A")
        self.uiPoseNameLE.selectAll()

    # ------------------- INIT ----------------------------------------------------
    def __init__(self, parent=None):
        super(BlurAddPose, self).__init__(parent)
        # load the ui
        self.parentWindow = parent
        QtCompat.loadUi(getUiFile(__file__), self)

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

        self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Add New Pose")

        self.refreshWindow()
