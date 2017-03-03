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

struct BindData {
    MPointArray inputPoints; /**< The world space points of the geometry to be
                                wrapped. */
    MFloatVectorArray
        driverNormals; /**< The world space normals of the driver geometry. */
    std::vector<MIntArray>
        perFaceVertices; /**< The per-face vertex ids of the driver. */
    std::vector<std::vector<MIntArray>>
        perFaceTriangleVertices; /**< The per-face per-triangle vertex ids of
                                    the driver. */
    /**
      Elements calculated in the threads.
    */
    std::vector<MIntArray> sampleIds;
    std::vector<MDoubleArray> weights;
    MMatrixArray bindMatrices;
    std::vector<BaryCoords> coords;
    std::vector<MIntArray> triangleVertices;
};

/**
  The cvWrap command is used to create new cvWrap deformers and to import and
  export wrap bindings.
*/
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
    // virtual MStatus  undoIt();
    // virtual MStatus  redoIt();
    virtual bool isUndoable() const;
    static void *creator();
    static MSyntax newSyntax();

    /**
      Distributes the ThreadData objects to the parallel threads.
      @param[in] data The user defined data.  In this case, the ThreadData
      array.
      @param[in] pRoot Maya's root task.
    */
    // static void CreateTasks(void *data, MThreadRootTask *pRoot);
    // static MThreadRetVal CalculateBindingTask(void *pParam);

    const static char *kName; /**< The name of the command. */

    /**
      Specifies the name of the cvWrap node.
    */
    const static char *kNameFlagShort;
    const static char *kNameFlagLong;

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

    /**
      Acquires the driver and driven dag paths from the input selection list.
    */
    MStatus GetGeometryPaths();

    /**
      Creates a new wrap deformer.
    */
    // MStatus CreateWrapDeformer();

    /**
      Gets the latest cvWrap node in the history of the deformed shape.
    */
    MStatus computeBarycenters(); // adding a pose

    MStatus GetLatestBlurSculptNode();
    MStatus setFaceVertexRelationShip();
    MStatus GetPreDeformedMesh(MObject &blurSculptNode, MDagPath &pathMesh);

    MStatus addAPose();                   // adding a pose
    MStatus addAFrame();                  // adding a pose
    MStatus getListPoses();               // get list of poses
    MStatus getListFrames(int poseIndex); // get list of frames

    /**
      Calculates the binding data for the wrap deformer to work.
      @param[in] pathBindMesh The path to the mesh to bind to.
      @param[in] bindData The structure containing all the bind information.
      @param[in,out] dgMod The modifier to hold all the plug operations.
    */
    // MStatus CalculateBinding(MDagPath& pathBindMesh, BindData& bindData,
    // MDGModifier& dgMod);

    /**
      Gets the MDagPath of any existing bind wrap mesh so we don't have to
      duplicate it for each new wrap.
      @param[out] pathBindMesh Storage for path to an existing bind mesh
    */
    // MStatus GetExistingBindMesh(MDagPath &pathBindMesh);

    /**
      Calculates new binding data for the selected components.
    */
    // MStatus Rebind();

    /**
      Get the bind mesh connected to the wrap node.
      @param[in] oWrapNode MObject to a cvWrap node..
      @param[out] pathBindMesh The path to the bind mesh.
    */
    // MStatus GetBindMesh(MObject& oWrapNode, MDagPath& pathBindMesh);

    /**
      Creates the mesh with the subset of faces used to calculate the rebind.
      @param[out] pathDriverSubset Path the new driver subset mesh.
    */
    // MStatus CreateRebindSubsetMesh(MDagPath& pathDriverSubset);

    MString name_;                 /**< Name of cvWrap node to create. */
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
