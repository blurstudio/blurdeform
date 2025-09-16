from Qt.QtCore import Qt, Property, Signal, Slot
from Qt.QtGui import QColor
from Qt.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QWidget,
    QComboBox,
)
from Qt import QtCompat
import os

RESOLVED_STYLESHEET_DEFAULT = """QLineEdit {color: rgba%(fg)s;
    background: rgba%(bg)s;
}"""


class LineEdit(QLineEdit):
    def dragEnterEvent(self, event):
        if not self.isReadOnly():
            event.acceptProposedAction()
        else:
            super(LineEdit, self).dragEnterEvent(event)

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if not self.isReadOnly() and mimeData.hasUrls():
            urlList = mimeData.urls()
            if urlList:
                fname = urlList[0].toLocalFile()
                self.setText(fname)
        event.acceptProposedAction()


class FilePickerWidget(QWidget):
    filenamePicked = Signal(str)
    filenameChanged = Signal(str)
    filenameEdited = Signal(str)

    def __init__(self, parent=None):
        self._correctBackground = QColor(156, 206, 156, 255)
        self._correctForeground = QColor(Qt.GlobalColor.white)
        self._inCorrectBackground = QColor(210, 156, 156, 255)
        self._inCorrectForeground = QColor(Qt.GlobalColor.white)
        self._defaultLocation = ""
        super(FilePickerWidget, self).__init__(parent)

        self.uiFilenameTXT = QComboBox(self)
        self.uiFilenameTXT.setEditable(True)
        self.uiPickFileBTN = QToolButton(self)
        self.uiPickFileBTN.setText("...")
        self.uiPickFileBTN.setToolTip(
            "<html><head/><body><p>Browse to a file path.</p><p>Ctrl + LMB: Explore to current path.</p></body></html>"
        )
        # Make this widget focusable and pass the widget focus to uiFilenameTXT
        self.setFocusProxy(self.uiFilenameTXT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout = QHBoxLayout(self)
        layout.addWidget(self.uiFilenameTXT)
        layout.addWidget(self.uiPickFileBTN)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._caption = "Pick file..."
        self._filters = "All Files (*.*)"
        self._pickFolder = False
        self._openFile = False
        self._resolvePath = False
        self._resolved = False
        self._chosenPath = None
        self._dropDownVisible = False

        self.uiFilenameTXT.editTextChanged.connect(self.emitFilenameChanged)
        self.uiFilenameTXT.lineEdit().editingFinished.connect(self.emitFilenameEdited)
        self.uiFilenameTXT.currentIndexChanged.connect(self.emitFilenameChanged)
        self.uiPickFileBTN.clicked.connect(self.pickPath)
        self.resolvedStylesheet = RESOLVED_STYLESHEET_DEFAULT

        self.resolve()

    def caption(self):
        return self._caption

    def emitFilenameChanged(self):
        self.resolve()
        if not self.signalsBlocked():
            self.filenameChanged.emit(self.uiFilenameTXT.currentText())

    def emitFilenameEdited(self):
        if not self.signalsBlocked():
            self.filenameEdited.emit(self.uiFilenameTXT.currentText())

    def filePath(self):
        return self._chosenPath or self.uiFilenameTXT.currentText()

    def filters(self):
        return self._filters

    def isResolved(self):
        return self._resolved

    def openFile(self):
        return self._openFile

    def pickFolder(self):
        return self._pickFolder

    def pickPath(self):
        initialPath = self.uiFilenameTXT.currentText() or self._defaultLocation
        print("initialPath ", initialPath)
        while not os.path.exists(initialPath):
            if os.path.dirname(initialPath) == initialPath:
                break
            else:
                initialPath = os.path.dirname(initialPath)
        if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            import subprocess

            # pull the filpath from the inputed initialPath
            fpath = os.path.normpath(initialPath)

            # run the file in windows
            if os.name == "nt":
                if os.path.isfile(fpath):
                    subprocess.Popen(r'explorer.exe /select, "{}"'.format(fpath))
                else:
                    subprocess.Popen(r'explorer.exe "{}"'.format(fpath))

            # run the file in linux
            elif os.name == "posix":
                raise RuntimeError("You have to set the browse command manually")
                # browseCmd = ""
                # subprocess.Popen(cmd % {'filepath': fpath}, shell=True)
            else:
                raise RuntimeError("OS not recognized")

        else:
            if self._pickFolder:
                filepath = QFileDialog.getExistingDirectory(
                    self, self._caption, initialPath
                )
            elif self._openFile:
                filepath, _ = QtCompat.QFileDialog.getOpenFileName(
                    self, self._caption, initialPath, self._filters
                )
            else:
                filepath, _ = QtCompat.QFileDialog.getSaveFileName(
                    self, self._caption, initialPath, self._filters
                )
            if filepath:
                self.uiFilenameTXT.setEditText(filepath)
                if not self.signalsBlocked():
                    self.filenamePicked.emit(filepath)

    def resolve(self):
        if self.resolvePath():
            path = self.uiFilenameTXT.currentText()
            if self._pickFolder:
                valid = os.path.isdir(path)
            else:
                valid = os.path.isfile(path)
            self._resolved = valid
        else:
            self._resolved = False

    def resolvePath(self):
        return self._resolvePath

    def setCaption(self, caption):
        self._caption = caption

    @Slot(str)
    def setFilePath(self, filePath):
        self.uiFilenameTXT.setEditText(filePath)
        self.resolve()

    def clearFilePathHistory(self):
        """Clears the path history."""
        self.uiFilenameTXT.blockSignals(True)
        self.uiFilenameTXT.lineEdit().blockSignals(True)
        txt = self.uiFilenameTXT.currentText()
        self.uiFilenameTXT.clear()
        self.uiFilenameTXT.setEditText(txt)
        self.uiFilenameTXT.lineEdit().blockSignals(False)
        self.uiFilenameTXT.blockSignals(False)

    def setFilePathHistory(self, filePathHistory):
        """Sets the paths stored in the combo box's drop down.

        Args:
            filePathHistory (list): A list of paths as strings.
        """
        self.uiFilenameTXT.blockSignals(True)
        self.uiFilenameTXT.lineEdit().blockSignals(True)
        txt = self.uiFilenameTXT.currentText()
        self.uiFilenameTXT.clear()
        self.uiFilenameTXT.addItems(filePathHistory)
        self.uiFilenameTXT.setEditText(txt)
        self.uiFilenameTXT.lineEdit().blockSignals(False)
        self.uiFilenameTXT.blockSignals(False)

    def filePathHistory(self):
        """Returns the list of paths stored as items in the combo box.

        Returns:
            list: A list of paths as strings.
        """
        history = []
        for idx in range(self.uiFilenameTXT.count()):
            history.append(self.uiFilenameTXT.itemText(idx))
        return history

    def setFilters(self, filters):
        self._filters = filters

    def setOpenFile(self, state):
        self._openFile = state

    def setPickFolder(self, state):
        self._pickFolder = state

    @Slot(bool)
    def setDropDownVisible(self, dropDownVisible):
        """Sets

        Args:
            dropDownVisible (TYPE): Description
        """
        if not dropDownVisible:
            css = (
                "QComboBox::drop-down {border-width: 0px;} "
                "QComboBox::down-arrow {image: url(noimg); border-width: 0px;}"
            )
        else:
            css = ""
        self.uiFilenameTXT.setStyleSheet(css)
        self._dropDownVisible = dropDownVisible

    def dropDownVisible(self):
        return self._dropDownVisible

    @Slot(bool)
    def setNotResolvePath(self, state):
        """Set resolvePath to the oposite of state."""
        self.setResolvePath(not state)

    @Slot(bool)
    def setResolvePath(self, state):
        self._resolvePath = state
        self.resolve()

    pyCaption = Property("QString", caption, setCaption)
    pyFilters = Property("QString", filters, setFilters)
    pyPickFolder = Property("bool", pickFolder, setPickFolder)
    pyOpenFile = Property("bool", openFile, setOpenFile)
    pyResolvePath = Property("bool", resolvePath, setResolvePath)
    pyFilePath = Property("QString", filePath, setFilePath)
    pyDropDownVisible = Property("bool", dropDownVisible, setDropDownVisible)

    # Load the colors from the stylesheets
    @Property(QColor)
    def correctBackground(self):
        return self._correctBackground

    @correctBackground.setter
    def correctBackground(self, color):
        self._correctBackground = color
        self.resolve()

    @Property(QColor)
    def correctForeground(self):
        return self._correctForeground

    @correctForeground.setter
    def correctForeground(self, color):
        self._correctForeground = color
        self.resolve()

    @Property(QColor)
    def inCorrectBackground(self):
        return self._inCorrectBackground

    @inCorrectBackground.setter
    def inCorrectBackground(self, color):
        self._inCorrectBackground = color
        self.resolve()

    @Property(QColor)
    def inCorrectForeground(self):
        return self._inCorrectForeground

    @inCorrectForeground.setter
    def inCorrectForeground(self, color):
        self._inCorrectForeground = color
        self.resolve()

    @Property("QString")
    def defaultLocation(self):
        return self._defaultLocation

    @defaultLocation.setter
    def defaultLocation(self, value):
        self._defaultLocation = str(value)
