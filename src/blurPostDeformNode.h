#ifndef __blurPostDeform_H__
#define __blurPostDeform_H__
#pragma once

// MAYA HEADER FILES:

#include "common.h"
#include <cassert>
#include <map>
#include <math.h>
#include <maya/MIOStream.h>
#include <maya/MStringArray.h>
#include <set>
#include <string.h>
#include <unordered_map>
#include <vector>

#include <maya/MItGeometry.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MPxDeformerNode.h>
#include <maya/MPxLocatorNode.h>

#include <maya/MFnCompoundAttribute.h>
#include <maya/MFnEnumAttribute.h>
#include <maya/MFnMatrixAttribute.h>
#include <maya/MFnMatrixData.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnStringData.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnUnitAttribute.h>
#include <maya/MItMeshVertex.h>

#include <maya/MAnimControl.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MFnPointArrayData.h>

#include <maya/MGlobal.h>
#include <maya/MPlug.h>
#include <maya/MTime.h>
#include <maya/MTypeId.h>

#include <maya/MArrayDataBuilder.h>
#include <maya/MArrayDataHandle.h>
#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>

#include <maya/MMatrix.h>
#include <maya/MPoint.h>
#include <maya/MVector.h>

#include <maya/MDagModifier.h>

#include <clew/clew_cl.h>
#include <maya/MFnMesh.h>
#include <maya/MGPUDeformerRegistry.h>
#include <maya/MOpenCLInfo.h>
#include <maya/MPxGPUDeformer.h>
#include <maya/MViewport2Renderer.h>

#include <maya/MFloatVectorArray.h>
#include <maya/MFnDoubleArrayData.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MMatrixArray.h>
#include <maya/MPointArray.h>

#define McheckErr(stat, msg)                                                   \
    if (MS::kSuccess != stat) {                                                \
        std::cout << msg;                                                      \
        return MS::kFailure;                                                   \
    }

// MAIN CLASS DECLARATION FOR THE CUSTOM NODE:
class blurSculpt : public MPxDeformerNode {
  public:
    blurSculpt();
    virtual ~blurSculpt();

    static void *creator();
    static MStatus initialize();

    // deformation function
    //
    virtual MStatus deform(
        MDataBlock &block, MItGeometry &iter, const MMatrix &mat,
        unsigned int multiIndex
    );

    void postConstructor();

    // when the accessory is deleted, this node will clean itself up
    //
    virtual MObject &accessoryAttribute() const;

    // create accessory nodes when the node is created
    //
    virtual MStatus accessoryNodeSetup(MDagModifier &cmd);

    MStatus sumDeformation(
        int geoIndex,
        MArrayDataHandle
            &deformationsHandle, // the current handle of the deformation
        MFnMesh &fnInputMesh,    // the current mesh
        float poseGainValue, float poseOffsetValue,
        float curentMult, // the pose multiplication of gain and value
        MMatrix &poseMat, MPoint &matPoint,
        // bool useSmoothNormals,
        int deformType, MIntArray &smoothTangentFound,
        MIntArray &smoothNormalFound,
        MIntArray &matrixNormalFound, // if we already have the tangets or not
        MFloatVectorArray &normals, MFloatVectorArray &smoothedNormals,
        MFloatVectorArray &tangents,
        MFloatVectorArray &smoothTangents, // the values of tangents and normals
        MMatrixArray &vertsMatrices,
        MPointArray &theVerticesSum
    ); // the output array to fill

  public:
    // local node attributes

    static MObject blurSculptMatrix; // blurSculpt center and axis

    static MTypeId id;

    static MObject inTime;        // the inTime
    static MObject uvSet;         // the uv set
    static MObject smoothNormals; // the uv set

    static MObject useMultiVectorMovement; // using multiVector movement
    static MObject poses;                  // array of all the poses

    static MObject poseName;
    static MObject poseGain;        // mult of the pose position
    static MObject poseOffset;      // add of the pose position
    static MObject poseEnabled;     // boolean for enable/disable Pose
    static MObject poseMatrix;      //  a matrix to calculate deformation from
    static MObject deformationType; // type of deformation (world, local, uv)

    static MObject deformations; // array of the deformations containing
    static MObject frame;        // float for the frame
    static MObject frameEnabled; // float for the frame
    static MObject gain;         // multier
    static MObject offset;       // added
    static MObject
        vectorMovements; // the vectors of movements // OLD AND DEPRECIATED
    static MObject storedVectors;        // multi geos stored mvts
    static MObject multiVectorMovements; // the array of vectors of movements
                                         // for multiGeometries

  private:
    // cached attributes

    std::vector<std::pair<std::vector<int>, std::vector<int>>>
        connectedVerticesMultiFlat; // connected Vertices Flat per Geometry
                                    // index, per vertex
    std::vector<std::pair<std::vector<int>, std::vector<int>>>
        connectedFacesMultiFlat; // connected Faces Flat

    std::vector<std::pair<std::vector<int>, std::vector<int>>>
        normalsVertsIdsMULTI; // vector of per vertex id of normals
    std::vector<std::pair<std::vector<int>, std::vector<int>>>
        tangentsVertsIdsMULTI; // vector of per vertex id of tangents
};

// the GPU override implementation of the blurSculptNode  Nothing damn

#endif
