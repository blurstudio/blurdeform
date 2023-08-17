##
#   :namespace  blurdev.blurdeform
#
#   :remarks    GUI to work with the blurSculpt plugin
#
#   :author     [author::email]
#   :author     [author::company]
#   :date       03/22/17
#

# make sure this is being run as the main process
if __name__ in ("__main__", "__builtin__"):
    # since this file is being executed in the main scope, we need to register the tool package to the sys.path
    import blurdev

    blurdev.registerScriptPath(__file__)

    import blurdeform
    from blurdeform.blurdeform import BlurDeformDialog

    dlg = blurdev.launch(BlurDeformDialog, instance=True)

    blurdeform.BLUR_DEFORM_UI_ROOT = dlg.parent()
    blurdeform.BLUR_DEFORM_UI = dlg
