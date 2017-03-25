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

    # depending on our environment, Python initializes the script differently for scope, so try both methods:
    # importing from a sub-module
    try:
        from blurdeform import BlurDeformDialog

    # importing from the main package
    except:
        from blurdeform.blurdeform import BlurDeformDialog

    blurdev.launch(BlurDeformDialog, instance=True)
