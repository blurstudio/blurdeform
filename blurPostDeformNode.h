#ifndef __blurPostDeform_H__
#define __blurPostDeform_H__
#pragma once

// MAYA HEADER FILES:

#include "common.h"
#include <math.h>
#include <maya/MIOStream.h>
#include <maya/MStringArray.h>
#include <string.h>

#include <maya/MItGeometry.h>
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

#include <maya/MArrayDataHandle.h>
#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>

#include <maya/MMatrix.h>
#include <maya/MPoint.h>
#include <maya/MVector.h>

#include <maya/MDagModifier.h>

#include <cassert>
#include <clew/clew_cl.h>
#include <maya/MFnMesh.h>
#include <maya/MGPUDeformerRegistry.h>
#include <maya/MOpenCLInfo.h>
#include <maya/MPxGPUDeformer.h>
#include <maya/MViewport2Renderer.h>
#include <vector>

#include <maya/MFloatVectorArray.h>
#include <maya/MFnDoubleArrayData.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MMatrixArray.h>
#include <maya/MPointArray.h>

#define McheckErr(stat, msg)                                                   \
    if (MS::kSuccess != stat) {                                                \
        cerr << msg;                                                           \
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

    // when the accessory is deleted, this node will clean itself up
    //
    virtual MObject &accessoryAttribute() const;

    // create accessory nodes when the node is created
    //
    virtual MStatus accessoryNodeSetup(MDagModifier &cmd);
    // MStatus setFrameVtx(MArrayDataHandle &deformationsHandle, MMatrix
    // poseMat, MPoint matPoint, int deformType, int frameIndex, int theMult,
    // float poseGainValue, float poseOffsetValue);
    MVector getTheTangent(
        MPointArray &deformedMeshVerticesPos,
        MArrayDataHandle &vertexTriangleIndicesData,
        MArrayDataHandle &triangleFaceValuesData,
        MArrayDataHandle &vertexVertexIndicesData,
        MArrayDataHandle &vertexFaceIndicesData, MFnMesh &fnInputMesh,
        MItMeshVertex &meshVertIt, int theVertexNumber, int deformType
    );

  public:
    // local node attributes

    static MObject blurSculptMatrix; // blurSculpt center and axis

    static MTypeId id;

    static MObject inTime;        // the inTime
    static MObject uvSet;         // the uv set
    static MObject smoothNormals; // the uv set

    static MObject vertexFaceIndices;   // store the vertex face relationship
    static MObject vertexVertexIndices; // store the vertex vertex relationship

    // structure to save relationShips
    static MObject vertexTriangleIndices; // store the vertex face relationship
    static MObject triangleFaceValues;    // array of all the triangles
    static MObject vertex1;               //
    static MObject vertex2;               //
    static MObject vertex3;               //
    static MObject uValue;                //
    static MObject vValue;                //

    static MObject poses; // array of all the poses

    static MObject poseName;
    static MObject poseGain;        // mult of the pose position
    static MObject poseOffset;      // add of the pose position
    static MObject poseEnabled;     // boolean for enable/disable Pose
    static MObject poseMatrix;      //  a matrix to calculate deformation from
    static MObject deformationType; // type of deformation (world, local, uv)

    static MObject deformations;    // array of the deformations containing
    static MObject frame;           // float for the frame
    static MObject frameEnabled;    // float for the frame
    static MObject gain;            // multier
    static MObject offset;          // added
    static MObject vectorMovements; // the vectors of movements

    /*
    private:
    bool getConnectedVerts(MItMeshVertex& meshIter, MIntArray& connVerts, int
    currVertIndex); static MVector getCurrNormal(MPointArray& inputPts,
    MIntArray& connVerts); bool inited; protected:
    */
};

// the GPU override implementation of the blurSculptNode
//

#endif