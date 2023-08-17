import os
import sys
from .Qt.QtCore import Qt
from .Qt.QtGui import QIcon
from .Qt.QtWidgets import QApplication, QMainWindow, QDialog, QSplashScreen


def getUiFile(fileVar, subFolder="ui", uiName=None):
    """Get the path to the .ui file

    Parameters
    ----------
    fileVar : str
            The __file__ variable passed from the invocation
    subFolder : str
            The folder to look in for the ui files. Defaults to 'ui'
    uiName : str or None
            The name of the .ui file. Defaults to the basename of
            fileVar with .ui instead of .py

    Returns
    -------
    str
            The path to the .ui file

    """
    uiFolder, filename = os.path.split(fileVar)
    if uiName is None:
        uiName = os.path.splitext(filename)[0]
    if subFolder:
        uiFile = os.path.join(uiFolder, subFolder, uiName + ".ui")
    return uiFile


def clearPathSymbols(paths, keepers=None):
    """Removes path symbols from the environment.

    This means I can unload my tools from the current process and re-import them
    rather than dealing with the always finicky reload()

    We use directory paths rather than module names because it gives us more control
    over what is unloaded

    Parameters
    ----------
    paths : list
            List of directory paths that will have their modules removed
    keepers : list or None
            List of module names that will not be removed (Default value = None)
    """
    keepers = keepers or []
    paths = [os.path.normcase(os.path.normpath(p)) for p in paths]

    for key, value in sys.modules.items():
        protected = False

        # Used by multiprocessing library, don't remove this.
        if key == "__parents_main__":
            protected = True

        # Protect submodules of protected packages
        if key in keepers:
            protected = True

        ckey = key
        while not protected and "." in ckey:
            ckey = ckey.rsplit(".", 1)[0]
            if ckey in keepers:
                protected = True

        if protected:
            continue

        try:
            packPath = value.__file__
        except AttributeError:
            continue

        packPath = os.path.normcase(os.path.normpath(packPath))

        isEnvPackage = any(packPath.startswith(p) for p in paths)
        if isEnvPackage:
            sys.modules.pop(key)


def getIcon(iconName):
    uiFolder = os.path.dirname(os.path.realpath(__file__))
    iconPth = os.path.join(uiFolder, "img", iconName + ".png")
    return QIcon(iconPth)


ICONS = {
    "Add": getIcon("Add"),
    "AddMeshToBlurNode": getIcon("plusMesh-button"),
    "Delete": getIcon("Delete"),
    "RmvMeshToBlurNode": getIcon("minusMesh-button"),
    "addFrame": getIcon("addFrame"),
    "backUp": getIcon("backUp"),
    "cancelEdit": getIcon("cancelEdit"),
    "disconnect": getIcon("disconnect"),
    "edit": getIcon(r"edit"),
    "empty": getIcon("empty"),
    "fromScene": getIcon("fromScene"),
    "gear": getIcon(r"gear"),
    "publish": getIcon("publish"),
    "refresh": getIcon("refresh"),
    "restore": getIcon("restore"),
    "toFrame": getIcon("toFrame"),
}


def rootWindow():
    """Returns the currently active QT main window
    Only works for QT UI's like Maya
    """
    # for MFC apps there should be no root window
    window = None
    if QApplication.instance():
        inst = QApplication.instance()
        window = inst.activeWindow()
        # Ignore QSplashScreen's, they should never be considered the root window.
        if isinstance(window, QSplashScreen):
            return None
        # If the application does not have focus try to find A top level widget
        # that doesn't have a parent and is a QMainWindow or QDialog
        if window is None:
            windows = []
            dialogs = []
            for w in QApplication.instance().topLevelWidgets():
                if w.parent() is None:
                    if isinstance(w, QMainWindow):
                        windows.append(w)
                    elif isinstance(w, QDialog):
                        dialogs.append(w)
            if windows:
                window = windows[0]
            elif dialogs:
                window = dialogs[0]

        # grab the root window
        if window:
            while True:
                parent = window.parent()
                if not parent:
                    break
                if isinstance(parent, QSplashScreen):
                    break
                window = parent
    return window


def launchDialog(parent, dialogClass, instance, modal=True, instanced=True):
    if instanced:
        if instance is None:
            dlg = dialogClass(parent=parent)
        else:
            dlg = instance
    else:
        dlg = dialogClass(parent=parent)

    if modal:
        dlg.exec_()
    else:
        dlg.show()
        dlg.raise_()
        dlg.setWindowState(
            dlg.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
    return dlg
