##
#   :namespace  blurdeform
#
#   :remarks    GUI to work with the blurSculpt plugin
#
#   :author     [author::email]
#   :author     [author::company]
#   :date       03/22/17
#

BLUR_DEFORM_UI = None
BLUR_DEFORM_UI_ROOT = None


def runBlurDeformUI():
    from maya import cmds
    from .utils import rootWindow
    from .blurdeform import BlurDeformDialog

    global BLUR_DEFORM_UI
    global BLUR_DEFORM_UI_ROOT

    if not cmds.pluginInfo("blurdeform", q=True, loaded=True):
        cmds.loadPlugin("blurdeform")

    # make and show the UI
    BLUR_DEFORM_UI_ROOT = rootWindow()
    # Keep a global reference around, otherwise it gets GC'd
    BLUR_DEFORM_UI = BlurDeformDialog(parent=BLUR_DEFORM_UI_ROOT)
    BLUR_DEFORM_UI.show()


def tool_paths():
    import os

    path = os.path.dirname(__file__)
    pathPar = os.path.dirname(path)
    return [path], [pathPar]
