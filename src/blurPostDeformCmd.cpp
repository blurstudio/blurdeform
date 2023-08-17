#include "blurPostDeformCmd.h"
#include "blurPostDeformNode.h"

#include <algorithm>
#include <cassert>
#include <maya/MArgDatabase.h>
#include <maya/MFnDoubleArrayData.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MFnMatrixData.h>
#include <maya/MFnMesh.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MFnWeightGeometryFilter.h>
#include <maya/MGlobal.h>
#include <maya/MItDependencyGraph.h>
#include <maya/MItGeometry.h>
#include <maya/MItSelectionList.h>
#include <maya/MMeshIntersector.h>
#include <maya/MSyntax.h>
#include <utility>

#define PROGRESS_STEP 100
#define TASK_COUNT 32

/**
  A version number used to support future updates to the binary wrap binding
  file.
*/
const float kWrapFileVersion = 1.0f;

const char *blurSculptCmd::kName = "blurSculpt";
const char *blurSculptCmd::kQueryFlagShort = "-q";
const char *blurSculptCmd::kQueryFlagLong = "-query";
const char *blurSculptCmd::kNameFlagShort = "-n";
const char *blurSculptCmd::kNameFlagLong = "-name";
const char *blurSculptCmd::kBlurSculptNameFlagShort = "-bn";
const char *blurSculptCmd::kBlurSculptNameFlagLong = "-blurSculptName";
const char *blurSculptCmd::kAddPoseNameFlagShort = "-ap";
const char *blurSculptCmd::kAddPoseNameFlagLong = "-addPose";
const char *blurSculptCmd::kPoseNameFlagShort = "-pn";
const char *blurSculptCmd::kPoseNameFlagLong = "-poseName";
const char *blurSculptCmd::kPoseTransformFlagShort = "-pt";
const char *blurSculptCmd::kPoseTransformFlagLong = "-poseTransform";
const char *blurSculptCmd::kListPosesFlagShort = "-lp";
const char *blurSculptCmd::kListPosesFlagLong = "-listPoses";
const char *blurSculptCmd::kListFramesFlagShort = "-lf";
const char *blurSculptCmd::kListFramesFlagLong = "-listFrames";
const char *blurSculptCmd::kAddFlagShort = "-add";
const char *blurSculptCmd::kAddFlagLong = "-addAtTime";
const char *blurSculptCmd::kOffsetFlagShort = "-of";
const char *blurSculptCmd::kOffsetFlagLong = "-offset";
const char *blurSculptCmd::kRemoveTimeFlagShort = "-rmv";
const char *blurSculptCmd::kRemoveTimeFlagLong = "-removeAtTime";
const char *blurSculptCmd::kHelpFlagShort = "-h";
const char *blurSculptCmd::kHelpFlagLong = "-help";

/**
  Displays command instructions.
*/
void DisplayHelp()
{
    MString help;
    help += "Flags:\n";
    help += "-name (-n):              String     Name of the blurSclupt node to create.\n";
    help += "-query (-q):             N/A        Query mode.\n";
    help += "-listPoses (-lp):        N/A        In query mode return the list of poses stored\n";
    help += "-listFrames (-lf):       N/A        combine with poseName and query mode\n";
    help += "                                        return the list of frame used\n";
    help += "-addPose (-ap):          N/A        Add a pose, use with poseName \n";
    help += "-poseName (-pn):         String     the name of the pose we want to add or edit\n";
    help += "-poseTransform (-pt):    String     the transform node for the pose to add\n";
    help += "-addAtTime (-nbm)        String     the mesh target to add at the currentTime\n";
    help += "                                        needs pose name\n";
    help += "-blurSculptName (-bn)    String     to Specify the sculptName for addAtTime\n";
    help += "-offset (-of)            Float      the offset distance to see if a vertex is moved\n";
    help += "                                        default 0.001 | used in addAtTime\n";
    help += "-removeAtTime (-rmv):    N/A        Remove this pose at this time\n";
    help += "-help (-h)               N/A        Display this text.\n";
    MGlobal::displayInfo(help);
}

blurSculptCmd::blurSculptCmd()
    : name_("blurSculpt#"), command_(kCommandCreate), getListPoses_(false),
      getListFrames_(false), connectTransform_(false), aOffset_(0.001),
      aPoseGain_(1), aPoseOffset_(0)
{
}

MSyntax blurSculptCmd::newSyntax()
{
    MSyntax syntax;
    syntax.addFlag(kQueryFlagShort, kQueryFlagLong);
    syntax.addFlag(kListPosesFlagShort, kListPosesFlagLong);
    syntax.addFlag(kListFramesFlagShort, kListFramesFlagLong);
    syntax.addFlag(kNameFlagShort, kNameFlagLong, MSyntax::kString);
    syntax.addFlag(
        kBlurSculptNameFlagShort, kBlurSculptNameFlagLong, MSyntax::kString
    );
    syntax.addFlag(kAddPoseNameFlagShort, kAddPoseNameFlagLong);
    syntax.addFlag(kPoseNameFlagShort, kPoseNameFlagLong, MSyntax::kString);
    syntax.addFlag(
        kPoseTransformFlagShort, kPoseTransformFlagLong, MSyntax::kString
    );
    syntax.addFlag(kAddFlagShort, kAddFlagLong, MSyntax::kString);
    syntax.addFlag(kOffsetFlagShort, kOffsetFlagLong, MSyntax::kDouble);
    syntax.addFlag(kRemoveTimeFlagShort, kRemoveTimeFlagLong);
    syntax.addFlag(kHelpFlagShort, kHelpFlagLong);
    syntax.setObjectType(MSyntax::kSelectionList, 0, 255);
    syntax.useSelectionAsDefault(true);
    return syntax;
}

void *blurSculptCmd::creator() { return new blurSculptCmd; }

bool blurSculptCmd::isUndoable() const
{
    return command_ == kCommandCreate; // Only creation will be undoable
}

MStatus blurSculptCmd::doIt(const MArgList &args)
{
    MStatus status;

    status = GatherCommandArguments(args);
    CHECK_MSTATUS_AND_RETURN_IT(status);

    status = GetGeometryPaths();
    CHECK_MSTATUS_AND_RETURN_IT(status);
    if (command_ == kCommandHelp) {
        return MS::kSuccess;
    }
    if (command_ == kCommandAddPoseAtTime) {
        status = GetLatestBlurSculptNode();
    }
    if (command_ == kCommandAddPose) {
        addAPose();
        return MS::kSuccess;
    }
    MFnDagNode fnMeshDriven(meshDeformed_);

    if (command_ == kCommandCreate) {

        // Add the blurSculpt creation command to the modifier.
        MString command = "deformer -type blurSculpt -n \"" + name_ + "\"";
        command += " " + fnMeshDriven.partialPathName();

        status = dgMod_.commandToExecute(command);
        status = dgMod_.doIt();
        status = GetLatestBlurSculptNode();

        MFnDependencyNode fnBlurSculptNode(oBlurSculptNode_);
        setResult(fnBlurSculptNode.name());
    }
    CHECK_MSTATUS_AND_RETURN_IT(status);
    status = getListPoses();
    CHECK_MSTATUS_AND_RETURN_IT(status);
    if (command_ == kCommandAddPoseAtTime) {
        status = GetLatestBlurSculptNode();
        MFnDependencyNode fnBlurSculptNode(oBlurSculptNode_);
        MGlobal::displayInfo(
            MString("Adding : [") + targetMeshAdd_ + MString("] to mesh [") +
            fnMeshDriven.partialPathName() + MString("]")
        );
        MGlobal::displayInfo(
            MString("       fnBlurSculptNode : ") + fnBlurSculptNode.name() +
            MString("[") + indexInDeformer + MString("]")
        );
        addAFrame();
    }
    else if (command_ == kCommandQuery) {
        int nb = allPosesNames_.length();
        if (getListPoses_) {
            MString toDisplay("the poses names : ");
            MString tst("test");

            for (int i = 0; i < nb; i++) {
                toDisplay += MString("[") + allPosesNames_[i] + MString("]");
                appendToResult(allPosesNames_[i].asChar());
            }
        }
        if (getListFrames_) {
            int poseIndex = getMStringIndex(allPosesNames_, poseName_);
            if (poseIndex == -1) {
                MGlobal::displayError(poseName_ + " is not a pose");
                return MS::kFailure;
            }
            else {
                getListFrames(poseIndex);
                MString toDisplay(
                    "the frame for pose " + poseName_ + " are : \n"
                );
                for (unsigned int i = 0; i < allFramesFloats_.length(); i++) {
                    toDisplay +=
                        MString(" [") + allFramesFloats_[i] + MString("]");
                    appendToResult(static_cast<float>(allFramesFloats_[i]));
                }
            }
        }
    }
    return MS::kSuccess;
}

MStatus blurSculptCmd::GatherCommandArguments(const MArgList &args)
{
    MStatus status;
    MArgDatabase argData(syntax(), args);
    argData.getObjects(selectionList_);
    if (argData.isFlagSet(kHelpFlagShort)) {
        command_ = kCommandHelp;
        DisplayHelp();
        return MS::kSuccess;
    }
    if (argData.isFlagSet(kNameFlagShort)) {
        name_ = argData.flagArgumentString(kNameFlagShort, 0, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }
    if (argData.isFlagSet(kBlurSculptNameFlagShort)) {
        blurSculptNameInput_ =
            argData.flagArgumentString(kBlurSculptNameFlagShort, 0, &status);
        blurSculptNameProvided_ = true;
    }
    if (argData.isFlagSet(kPoseNameFlagShort)) {
        poseName_ = argData.flagArgumentString(kPoseNameFlagShort, 0, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }
    if (argData.isFlagSet(kQueryFlagShort)) {
        command_ = kCommandQuery;
    }
    if (argData.isFlagSet(kListPosesFlagShort)) {
        getListPoses_ = true;
    }
    if (argData.isFlagSet(kListFramesFlagShort)) {
        getListFrames_ = true;
    }
    if (command_ == kCommandQuery)
        return MS::kSuccess;

    if (argData.isFlagSet(kPoseTransformFlagShort)) {
        poseTransformStr_ =
            argData.flagArgumentString(kPoseTransformFlagShort, 0, &status);
        MSelectionList selListA;
        MGlobal::getSelectionListByName(poseTransformStr_, selListA);
        selListA.getDependNode(0, poseTransform_);
        selListA.clear();
        connectTransform_ = true;
    }

    if (argData.isFlagSet(kOffsetFlagShort)) {
        MString OffsetStr =
            argData.flagArgumentString(kOffsetFlagShort, 0, &status);
        aOffset_ = OffsetStr.asFloat();
    }

    if (argData.isFlagSet(kAddPoseNameFlagShort)) {
        command_ = kCommandAddPose;
        return MS::kSuccess;
    }
    if (argData.isFlagSet(kAddFlagShort)) {
        targetMeshAdd_ = argData.flagArgumentString(kAddFlagShort, 0, &status);
        MSelectionList selList;
        MGlobal::getSelectionListByName(targetMeshAdd_, selList);
        selList.getDagPath(0, meshTarget_);
        selList.clear();
        status = GetShapeNode(meshTarget_);

        command_ = kCommandAddPoseAtTime;
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }
    else {
        command_ = kCommandCreate;
    }
    return MS::kSuccess;
}

MStatus blurSculptCmd::GetGeometryPaths()
{
    MStatus status;
    if (selectionList_.length() == 0) {
        MGlobal::displayError("select at least a mesh");
        return MS::kFailure;
    }
    if (command_ == kCommandQuery || command_ == kCommandHelp ||
        command_ == kCommandAddPose) {
        MObject inputNode;
        status = selectionList_.getDependNode(0, inputNode);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        MFnDependencyNode inputNodeDep(inputNode, &status);
        if (inputNodeDep.typeId() == blurSculpt::id) {
            oBlurSculptNode_ = inputNode;
            return MS::kSuccess;
        }
    }
    else {
        // The driver is selected last
        status = selectionList_.getDagPath(0, meshDeformed_);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        status = GetShapeNode(meshDeformed_);
        // The driver must be a mesh for this specific algorithm.
        if (command_ == kCommandCreate && !meshDeformed_.hasFn(MFn::kMesh)) {
            MGlobal::displayError("blurSculpt works only on  mesh.");
            return MS::kFailure;
        }
    }

    return MS::kSuccess;
}

MStatus blurSculptCmd::GetLatestBlurSculptNode()
{
    MStatus status;
    MObject oDriven = meshDeformed_.node();

    // Since we use MDGModifier to execute the deformer command, we can't get
    // the created deformer node, so we need to find it in the deformation
    // chain.
    MItDependencyGraph itDG(
        oDriven, MFn::kGeometryFilt, MItDependencyGraph::kUpstream,
        MItDependencyGraph::kDepthFirst, MItDependencyGraph::kNodeLevel, &status
    );
    CHECK_MSTATUS_AND_RETURN_IT(status);
    MObject oDeformerNode;
    for (; !itDG.isDone(); itDG.next()) {
        oDeformerNode = itDG.currentItem();
        MFnDependencyNode fnNode(oDeformerNode, &status);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        if (fnNode.typeId() == blurSculpt::id) {
            if (blurSculptNameProvided_ &&
                fnNode.name() != blurSculptNameInput_) {
                continue;
            }
            oBlurSculptNode_ = oDeformerNode;
            MPlug thisPlug = itDG.thisPlug();
            indexInDeformer = thisPlug.logicalIndex();
            return MS::kSuccess;
        }
    }
    return MS::kFailure;
}

MStatus blurSculptCmd::getListPoses()
{
    MStatus status;
    allPosesNames_.clear();
    allPosesIndices_.clear();

    MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
    // get list of poses

#if MAYA_API_VERSION > 201900
    MPlug posesPlug =
        blurSculptDepNode.findPlug(blurSculpt::poses, true, &status);
#else
    MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
#endif

    unsigned int nbPoses = posesPlug.numElements(&status);

    unsigned nEle =
        posesPlug.getExistingArrayAttributeIndices(allPosesIndices_, &status);

    for (unsigned int element = 0; element < nbPoses; element++) {
        // do not use elementByLogicalIndex
        MPlug thePosePlug = posesPlug.elementByPhysicalIndex(element, &status);
        MPlug thePoseNamePlug = thePosePlug.child(blurSculpt::poseName);
        allPosesNames_.append(thePoseNamePlug.asString());
    }
    return MS::kSuccess;
}

MStatus blurSculptCmd::getListFrames(int poseIndex)
{
    MStatus status;
    allFramesFloats_.clear();

    MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);

#if MAYA_API_VERSION > 201900
    MPlug posesPlug =
        blurSculptDepNode.findPlug(blurSculpt::poses, true, &status);
#else
    MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
#endif

    MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);

    MPlug deformationsPlug = thePosePlug.child(blurSculpt::deformations);
    unsigned int nbDeformations = deformationsPlug.numElements(&status);
    // get the frame indices
    unsigned nEle = deformationsPlug.getExistingArrayAttributeIndices(
        allFramesIndices_, &status
    );
    for (unsigned int deformIndex = 0; deformIndex < nbDeformations;
         deformIndex++) {
        MPlug theDeformPlug =
            deformationsPlug.elementByPhysicalIndex(deformIndex, &status);
        MPlug theFramePlug = theDeformPlug.child(blurSculpt::frame);
        allFramesFloats_.append(theFramePlug.asFloat());
    }
    return MS::kSuccess;
}

MStatus blurSculptCmd::addAPose()
{
    MStatus status;

    MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
    // get list of poses
#if MAYA_API_VERSION > 201900
    MPlug posesPlug =
        blurSculptDepNode.findPlug(blurSculpt::poses, true, &status);
#else
    MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
#endif
    // get the index of the poseName in the array
    int tmpInd = getMStringIndex(
        allPosesNames_, poseName_
    ); // allPosesNames_.indexOf(poseName_);
    int poseIndex;

    bool doAddName = false;
    if (tmpInd == -1) { // if doesn't exists use new one
        poseIndex = GetFreeIndex(posesPlug);
        doAddName = true;
    }
    else {
        poseIndex = allPosesIndices_[tmpInd];
    }
    if (doAddName) {
        // access the channel
        MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);
        // add the channel Name
        MDGModifier dgMod;
        MPlug thePoseMatrixPlug = thePosePlug.child(blurSculpt::poseMatrix);

        MPlug thePoseNamePlug = thePosePlug.child(blurSculpt::poseName);
        thePoseNamePlug.setValue(poseName_);
        MPlug thePoseGainPlug = thePosePlug.child(blurSculpt::poseGain);
        thePoseGainPlug.setValue(1.0);

        MPlug thePoseOffsetPlug = thePosePlug.child(blurSculpt::poseOffset);
        thePoseOffsetPlug.setValue(0.0);

        if (connectTransform_) {
            // add the transform
            MFnDependencyNode poseTransformDep_(poseTransform_);

#if MAYA_API_VERSION > 201900
            MPlug worldMatPlug = poseTransformDep_.findPlug("matrix", true);
#else
            MPlug worldMatPlug = poseTransformDep_.findPlug("matrix");
#endif
            dgMod.connect(worldMatPlug, thePoseMatrixPlug);
            dgMod.doIt();
        }
    }
    return MS::kSuccess;
}

MStatus blurSculptCmd::addAFrame()
{
    MStatus status;

    // get the meshes access
    MFnMesh fnDeformedMesh(meshDeformed_, &status);
    MFnMesh fnTargetMesh(meshTarget_, &status);
    // get access to our node
    MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
    // get list of poses

#if MAYA_API_VERSION > 201900
    MPlug posesPlug =
        blurSculptDepNode.findPlug(blurSculpt::poses, true, &status);
#else
    MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
#endif

    // get the nb of vertices
    int nbDeformedVtx = fnDeformedMesh.numVertices();
    int nbTargetVtx = fnTargetMesh.numVertices();

    if (nbDeformedVtx != nbTargetVtx) {
        MGlobal::displayError("not same number of vertices");
        return MS::kFailure;
    }

    // get the current time
    MTime currentFrame = MAnimControl::currentTime();
    float currentFrameF = float(currentFrame.value());

    MGlobal::displayInfo(MString("offset value : ") + aOffset_);

    // get the mode of deformation
    // get the index of the poseName in the array
    int tmpInd = getMStringIndex(
        allPosesNames_, poseName_
    ); // allPosesNames_.indexOf(poseName_);

    if (tmpInd == -1) { // if doesn't exists create new one
        addAPose();     // add the pose
        getListPoses(); // get the list
        int tmpInd = getMStringIndex(
            allPosesNames_, poseName_
        ); // allPosesNames_.indexOf(poseName_);
    }
    int poseIndex = allPosesIndices_[tmpInd];

    // access the channel
    MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);

    // get the Matrix
    MDGModifier dgMod;
    MPoint matPoint(0, 0, 0);
    MPlug thePoseMatrixPlug = thePosePlug.child(blurSculpt::poseMatrix);

    MObject matrixObj;
    thePoseMatrixPlug.getValue(matrixObj);
    MFnMatrixData mData(matrixObj);
    MMatrix matrixValue = mData.matrix(&status);
    matPoint = matPoint * matrixValue;
    MMatrix matrixValueInverse = matrixValue.inverse();
    MPlug poseEnabledPlug = thePosePlug.child(blurSculpt::poseEnabled);

    MPlug deformationTypePlug = thePosePlug.child(blurSculpt::deformationType);
    int deformationType = deformationTypePlug.asInt();

    // get the deformations plug
    getListFrames(poseIndex);
    MPlug theDeformationPlug = thePosePlug.child(blurSculpt::deformations);

    // we get the list of frames for the pose
    int deformationIndex = -1;
    bool emptyFrameChannel = false;
    for (unsigned int i = 0; i < allFramesFloats_.length(); i++) {
        if (currentFrameF == allFramesFloats_[i]) {
            // work with the indices
            deformationIndex = allFramesIndices_[i];
            emptyFrameChannel = true;
            break;
        }
    }

    if (deformationIndex == -1)
        deformationIndex = GetFreeIndex(theDeformationPlug);

    // get the new deformation
    MPlug deformPlug =
        theDeformationPlug.elementByLogicalIndex(deformationIndex, &status);
    // set the frame value
    MPlug theFramePlug = deformPlug.child(blurSculpt::frame);
    theFramePlug.setValue(currentFrameF);

    // MPlug theVectorsPlug = deformPlug.child(blurSculpt::vectorMovements);
    MPlug storedVectorsPlug = deformPlug.child(blurSculpt::storedVectors);
    MPlug storedVectorsPlugIndex =
        storedVectorsPlug.elementByLogicalIndex(indexInDeformer, &status);
    MPlug theVectorsPlug =
        storedVectorsPlugIndex.child(blurSculpt::multiVectorMovements);

    // get the points from the meshes
    MPointArray deformedMeshVerticesPos;
    poseEnabledPlug.setValue(false);
    fnDeformedMesh.getPoints(deformedMeshVerticesPos, MSpace::kObject);

    MPointArray targetMeshVerticesPos;
    fnTargetMesh.getPoints(targetMeshVerticesPos, MSpace::kObject);

    MPoint offsetPoint;
    MMatrix mMatrix;

    MPlug facePlug, vertexPlug, vertexTrianglePlug, triangleValuesPlug;
    MVector normal, tangent, binormal, cross;
    MPoint DFV, TV;

    //// HERE THE NORMALS !!!
    MFloatVectorArray normals(nbDeformedVtx), tangents(nbDeformedVtx);
    MFloatVectorArray smoothTangents(nbDeformedVtx),
        smoothedNormals(nbDeformedVtx);
    MIntArray smoothTangentFound(nbDeformedVtx, -1),
        smoothNormalFound(nbDeformedVtx, -1); // init at -1

    std::vector<int> connectedVerticesFlat; // a flat array of all vertices
    std::vector<int>
        connectedVerticesIndicesFlat; // the indices of where to start in array
                                      // smooth the normals
#if MAYA_API_VERSION > 201900
    MPlug smoothNormalsPlug =
        blurSculptDepNode.findPlug(blurSculpt::smoothNormals, true);
#else
    MPlug smoothNormalsPlug =
        blurSculptDepNode.findPlug(blurSculpt::smoothNormals);
#endif

    int smoothNormalsRepeat = smoothNormalsPlug.asInt();

    if (deformationType != 0) { // tangent and normals
        connectedVerticesIndicesFlat.resize(nbDeformedVtx + 1);
        MItMeshVertex vertexIter(meshDeformed_);
        int sumConnectedVertices = 0;
        int sumConnectedFaces = 0;
        for (int vtxTmp = 0; !vertexIter.isDone();
             vertexIter.next(), ++vtxTmp) {
            MIntArray surroundingVertices, surroundingFaces;
            int vtxIndex = vertexIter.index();

            vertexIter.getConnectedVertices(surroundingVertices);
            vertexIter.getConnectedFaces(surroundingFaces);

            // we try to store in a flat array maybe better access
            // ------------------
            int nbConnVerts = surroundingVertices.length();
            connectedVerticesIndicesFlat[vtxIndex] = sumConnectedVertices;
            for (int k = 0; k < nbConnVerts; ++k)
                connectedVerticesFlat.push_back(surroundingVertices[k]);
            sumConnectedVertices += nbConnVerts;
        }

        fnDeformedMesh.getVertexNormals(false, normals, MSpace::kWorld);

        for (int theVertexNumber = 0; theVertexNumber < nbDeformedVtx;
             ++theVertexNumber) {
            MVector tangent =
                getVertexTangent(fnDeformedMesh, vertexIter, theVertexNumber);
            tangents.set(tangent, theVertexNumber);
        }

        for (int it = 0; it < smoothNormalsRepeat; ++it) {
            for (int theVertexNumber = 0; theVertexNumber < nbDeformedVtx;
                 ++theVertexNumber) {
                getSmoothedVector(
                    theVertexNumber, smoothNormalFound, normals,
                    smoothedNormals, connectedVerticesFlat,
                    connectedVerticesIndicesFlat
                );
                smoothNormalFound[theVertexNumber] = -1;
            }
            normals = smoothedNormals;
        }
    }

    // Store vectors values
    MPoint zeroPt(0, 0, 0);
    for (int indVtx = 0; indVtx < nbTargetVtx; indVtx++) {
        DFV = deformedMeshVerticesPos[indVtx];
        TV = targetMeshVerticesPos[indVtx];
        if (DFV.distanceTo(TV) > aOffset_) {
            if (deformationType == 0) {
                offsetPoint =
                    TV * matrixValueInverse - DFV * matrixValueInverse;
            }
            else {
                normal = normals[indVtx];
                tangent = tangents[indVtx];
                CreateMatrix(zeroPt, normal, tangent, mMatrix);
                offsetPoint = (TV - DFV) * mMatrix.inverse();
            }
            MFnNumericData fnNumericData;
            MObject vectorValues =
                fnNumericData.create(MFnNumericData::k3Float, &status);

            fnNumericData.setData3Float(
                float(offsetPoint.x), float(offsetPoint.y), float(offsetPoint.z)
            );
            CHECK_MSTATUS_AND_RETURN_IT(status);

            MPlug VectorsPlugElement =
                theVectorsPlug.elementByLogicalIndex(indVtx, &status);
            CHECK_MSTATUS_AND_RETURN_IT(status);
            status = dgMod.newPlugValue(VectorsPlugElement, vectorValues);
            CHECK_MSTATUS_AND_RETURN_IT(status);
        }
    }
    poseEnabledPlug.setValue(true);
    status = dgMod.doIt();
    CHECK_MSTATUS_AND_RETURN_IT(status);

    return MS::kSuccess;
}
