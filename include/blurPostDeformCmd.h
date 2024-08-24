#ifndef blurPostDeformCmd_H
#define blurPostDeformCmd_H

#include <maya/MArgList.h>
#include <maya/MDGModifier.h>
#include <maya/MDagPath.h>
#include <maya/MDagPathArray.h>
#include <maya/MFloatArray.h>
#include <maya/MFloatVectorArray.h>
#include <maya/MFnPointArrayData.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MItMeshVertex.h>
#include <maya/MMatrixArray.h>
#include <maya/MMeshIntersector.h>
#include <maya/MObjectArray.h>
#include <maya/MPlug.h>
#include <maya/MPointArray.h>
#include <maya/MSelectionList.h>
#include <maya/MString.h>
#include <maya/MStringArray.h>
#include <maya/MThreadPool.h>

#include <maya/MAnimControl.h>
#include <maya/MPxCommand.h>

#include <fstream>
#include <iostream>
#include <map>
#include <math.h>
#include <stdio.h>
#include <vector>

#include "common.h"

class blurSculptCmd : public MPxCommand {
  public:
    enum CommandMode {
        kCommandCreate,
        kCommandQuery,
        kCommandAddPose,
        kCommandAddPoseAtTime,
        kCommandHelp
    };
    blurSculptCmd();
    virtual MStatus doIt(const MArgList &);
    virtual bool isUndoable() const;
    static void *creator();
    static MSyntax newSyntax();

    const static char *kName; /**< The name of the command. */

    /**
      Specifies the name of the cvWrap node.
    */
    const static char *kNameFlagShort;
    const static char *kNameFlagLong;

    const static char *kBlurSculptNameFlagShort;
    const static char *kBlurSculptNameFlagLong;

    const static char *kQueryFlagShort;
    const static char *kQueryFlagLong;

    const static char *kAddPoseNameFlagShort;
    const static char *kAddPoseNameFlagLong;

    const static char *kPoseNameFlagShort;
    const static char *kPoseNameFlagLong;

    const static char *kPoseTransformFlagShort;
    const static char *kPoseTransformFlagLong;

    const static char *kListPosesFlagShort;
    const static char *kListPosesFlagLong;

    const static char *kListFramesFlagShort;
    const static char *kListFramesFlagLong;

    const static char *kAddFlagShort;
    const static char *kAddFlagLong;

    const static char *kOffsetFlagShort;
    const static char *kOffsetFlagLong;

    const static char *kRemoveTimeFlagShort;
    const static char *kRemoveTimeFlagLong;

    /**
      Displays help.
    */
    const static char *kHelpFlagShort;
    const static char *kHelpFlagLong;

  private:
    /**
      Gathers all the command arguments and sets necessary command states.
      @param[in] args Maya MArgList.
    */
    MStatus GatherCommandArguments(const MArgList &args);

    MStatus GetGeometryPaths();

    MStatus GetLatestBlurSculptNode();

    MStatus addAPose();                   // adding a pose
    MStatus addAFrame();                  // adding a pose
    MStatus getListPoses();               // get list of poses
    MStatus getListFrames(int poseIndex); // get list of frames

    MString name_; /**< Name of blurSculpt node to create. */
    MString blurSculptNameInput_ =
        ""; /**< Name of the blurSculpt as an input. */
    bool blurSculptNameProvided_ = false;
    MString poseName_;             /**< name of the pose to work with. */
    MString targetMeshAdd_;        /**< name of the target mesh to compute the
                                      deformation for the current time  */
    MString poseTransformStr_;     /**< name of the target mesh to compute the
                                      deformation for the current time  */
    CommandMode command_;          // the command type
    MSelectionList selectionList_; /**< Selected command input nodes. */
    MObject oBlurSculpt_; /**< MObject to the BlurSculpt node in focus. */
    MDGModifier dgMod_;   // the execute of mel

    MDagPath meshDeformed_; /**< Paths to the shape deformed */
    int indexInDeformer;    // index of the mesh in the deformer
    MDagPath meshTarget_;   /**< Paths to the target mesh*/
    MObject poseTransform_;

    MObject oBlurSculptNode_; /**< MObject to the blurSculpt node in focus. */
    bool getListPoses_;
    bool getListFrames_;
    bool connectTransform_;
    float aOffset_;
    float aPoseGain_;
    float aPoseOffset_;

    MStringArray allPosesNames_;
    MFloatArray allFramesFloats_;
    MIntArray allFramesIndices_, allPosesIndices_;
};

#endif
