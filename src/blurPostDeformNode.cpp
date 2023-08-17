#include "blurPostDeformNode.h"
#include "setOverloads.h"

MTypeId blurSculpt::id(0x001226F0);
// local attributes
//
MObject blurSculpt::blurSculptMatrix;
MObject blurSculpt::uvSet;
MObject blurSculpt::smoothNormals;
MObject blurSculpt::useMultiVectorMovement;
MObject blurSculpt::deformationType;
MObject blurSculpt::inTime;

MObject blurSculpt::poses; // array of all the poses
MObject blurSculpt::poseName;
MObject blurSculpt::poseGain;     // mult of the pose position
MObject blurSculpt::poseOffset;   // add of the pose position
MObject blurSculpt::poseEnabled;  // boolean for enable/disable Pose
MObject blurSculpt::poseMatrix;   // a matrix to calculate deformation from
MObject blurSculpt::deformations; // array of the deformations containing
MObject blurSculpt::frame;        // float for the frame
MObject blurSculpt::frameEnabled;
MObject blurSculpt::gain;                 // multier
MObject blurSculpt::offset;               // added
MObject blurSculpt::vectorMovements;      // the vectors of movements
MObject blurSculpt::storedVectors;        // multi geos stored mvts
MObject blurSculpt::multiVectorMovements; // the array of vectors of movements
                                          // for multiGeometries

blurSculpt::blurSculpt() {}
blurSculpt::~blurSculpt() {}
void *blurSculpt::creator() { return new blurSculpt(); }

void blurSculpt::postConstructor() { setExistWithoutInConnections(true); }

MStatus blurSculpt::sumDeformation(
    int geoIndex,
    MArrayDataHandle
        &deformationsHandle, // the current handle of the deformation
    MFnMesh &fnInputMesh,    // the current mesh
    float poseGainValue, float poseOffsetValue,
    float curentMult, // the pose multiplication of gain and value
    MMatrix &poseMat, MPoint &matPoint, int deformType,
    MIntArray &smoothTangentFound, MIntArray &smoothNormalFound,
    MIntArray &matrixNormalFound, // if we already have the tangets or not
    MFloatVectorArray &normals, MFloatVectorArray &smoothedNormals,
    MFloatVectorArray &tangents,
    MFloatVectorArray &smoothTangents, // the values of tangents and normals
    MMatrixArray &vertsMatrices,
    MPointArray &theVerticesSum
) // the output array to fill
{
    MStatus returnStatus;
    MDataHandle deformationFrameHandle =
        deformationsHandle.inputValue(&returnStatus);
    McheckErr(returnStatus, "Error getting deformationFrameHandle\n");

    // VECTORS
    auto myPair = connectedVerticesMultiFlat[geoIndex];
    std::vector<int> connectedVerticesFlat = myPair.first;
    std::vector<int> connectedVerticesIndicesFlat = myPair.second;

    float gainValue = deformationFrameHandle.child(gain).asFloat();
    float offsetValue = deformationFrameHandle.child(offset).asFloat();
    float multiplier = curentMult * (poseGainValue + poseOffsetValue) *
                       (gainValue + offsetValue);

    MArrayDataHandle storedVectorsHandle =
        deformationFrameHandle.child(storedVectors);

    // don't use jumpToArrayElement very very very bad
    MStatus checkExitsStatus = storedVectorsHandle.jumpToElement(geoIndex);

    if (MStatus::kSuccess != checkExitsStatus) {
        // if this index doesnt exists, it's not an empty,
        // it hasen't been stored, we deal as if the frame
        // is diabled
        return MStatus::kFailure;
    }
    MDataHandle child_hdl = storedVectorsHandle.inputValue(&returnStatus);
    MArrayDataHandle multiVectorMovementsHandle =
        child_hdl.child(multiVectorMovements);

    int nbVectorMvts = multiVectorMovementsHandle.elementCount();

    MFloatVector tangent, normal;
    int theVertexNumber;
    MDataHandle vectorHandle;

    MMatrix mMatrix;
    MPoint zeroPt(0, 0, 0);
    MPoint theValue;

    for (int vectorIndex = 0; vectorIndex < nbVectorMvts; vectorIndex++) {
        vectorHandle = multiVectorMovementsHandle.inputValue(&returnStatus);
        theVertexNumber = multiVectorMovementsHandle.elementIndex();

        if (MS::kSuccess != returnStatus) {
            std::cout << "Error getting deformationFrameHandle " << vectorIndex
                      << endl;
        }
        else {
            float3 &vtxValue = vectorHandle.asFloat3();
            if (deformType == 0) {
                theValue = MPoint(
                    multiplier * vtxValue[0], multiplier * vtxValue[1],
                    multiplier * vtxValue[2]
                );
                theValue = theValue * poseMat - matPoint;
            }
            else { // using normals
                if (matrixNormalFound[theVertexNumber] == 1) {
                    mMatrix = vertsMatrices[theVertexNumber];
                }
                else {
                    normal = normals[theVertexNumber];
                    tangent = tangents[theVertexNumber];
                    CreateMatrix(zeroPt, normal, tangent, mMatrix);
                    vertsMatrices[theVertexNumber] = mMatrix;
                    matrixNormalFound[theVertexNumber] = 1;
                }
                theValue =
                    MPoint(
                        multiplier * vtxValue[0], multiplier * vtxValue[1],
                        multiplier * vtxValue[2]
                    ) *
                    mMatrix;
            }
            theValue += theVerticesSum[theVertexNumber];
            theVerticesSum.set(theValue, theVertexNumber);
        }
        multiVectorMovementsHandle.next();
    }
    return returnStatus;
}

MStatus blurSculpt::initialize()
{
    // local attribute initialization
    MStatus stat;
    MFnMatrixAttribute mAttr;
    MFnStringData stringFn;
    MFnTypedAttribute tAttr;
    MFnEnumAttribute enumAttr;
    MFnUnitAttribute unitAttr;
    MFnCompoundAttribute cAttr;
    MFnNumericAttribute nAttr;

    blurSculptMatrix = mAttr.create("locateMatrix", "lm");
    mAttr.setStorable(false);
    mAttr.setConnectable(true);

    //  deformation attributes
    addAttribute(blurSculptMatrix);
    // the UV attribute
    MObject defaultString;
    defaultString = stringFn.create("HIII");
    uvSet = tAttr.create("uvSet", "uvs", MFnData::kString, defaultString);
    tAttr.setStorable(true);
    tAttr.setKeyable(false);
    addAttribute(uvSet);

    useMultiVectorMovement = nAttr.create(
        "useMultiVectorMovement", "umvm", MFnNumericData::kBoolean, false
    );
    nAttr.setStorable(true);
    nAttr.setHidden(true);
    addAttribute(useMultiVectorMovement);

    // the type of deformation
    deformationType =
        nAttr.create("deformationType", "dt", MFnNumericData::kInt, 0);
    nAttr.setStorable(true);
    nAttr.setHidden(true);

    inTime = unitAttr.create("inTime", "it", MFnUnitAttribute::kTime);
    unitAttr.setStorable(true);
    unitAttr.setKeyable(false);
    unitAttr.setWritable(true);
    unitAttr.setReadable(false);
    addAttribute(inTime);

    smoothNormals =
        nAttr.create("smoothNormalsRepeat", "snr", MFnNumericData::kInt, 0);
    nAttr.setKeyable(true);
    nAttr.setStorable(true);
    addAttribute(smoothNormals);

    // add the stored poses
    // the string for the name of the pose
    MObject poseNameS = stringFn.create("name Of pose");
    poseName =
        tAttr.create("poseName", "poseName", MFnData::kString, poseNameS);
    tAttr.setStorable(true);
    // the global gain of the pose
    poseGain = nAttr.create("poseGain", "poseGain", MFnNumericData::kFloat, 1.);
    // the global offset of the pose
    poseOffset =
        nAttr.create("poseOffset", "poseOffset", MFnNumericData::kFloat, 0.);
    poseEnabled = nAttr.create(
        "poseEnabled", "poseEnabled", MFnNumericData::kBoolean, true
    );
    nAttr.setKeyable(false);
    // matrix to calculate deformation from
    poseMatrix = mAttr.create("poseMatrix", "poseMatrix");
    mAttr.setStorable(false);
    mAttr.setConnectable(true);

    // the frame for the pose
    frame = nAttr.create("frame", "frame", MFnNumericData::kFloat);
    // the gain of the deformation
    frameEnabled = nAttr.create(
        "frameEnabled", "frameEnabled", MFnNumericData::kBoolean, true
    );
    nAttr.setKeyable(false);

    gain = nAttr.create("gain", "gain", MFnNumericData::kFloat, 1.0);
    // the offset of the deformation
    offset = nAttr.create("offset", "offset", MFnNumericData::kFloat, 0.);

    // the vectorMovement of the vertices	------- needs to be array of arrays
    // .... damn
    vectorMovements = nAttr.create(
        "vectorMovements", "vectorMovements", MFnNumericData::k3Float
    );
    nAttr.setArray(true);

    // the vectorMovement of the vertices	------- needs to be array of arrays
    // .... damn
    multiVectorMovements = nAttr.create(
        "multiVectorMovements", "mVectorMovements", MFnNumericData::k3Float
    );
    nAttr.setArray(true);

    // multi geometries stored mvts -------
    storedVectors = cAttr.create("storedVectors", "storedVectors");
    cAttr.setArray(true);
    cAttr.setUsesArrayDataBuilder(true);
    cAttr.setStorable(true);
    cAttr.setHidden(true);
    cAttr.addChild(multiVectorMovements);

    // create the compound object
    deformations = cAttr.create("deformations", "deformations");
    cAttr.setArray(true);
    cAttr.setUsesArrayDataBuilder(true);
    cAttr.setStorable(true);
    cAttr.setHidden(true);
    cAttr.addChild(frame);
    cAttr.addChild(frameEnabled);
    cAttr.addChild(gain);
    cAttr.addChild(offset);
    cAttr.addChild(vectorMovements);
    cAttr.addChild(storedVectors);

    // create the compound object
    poses = cAttr.create("poses", "poses");
    cAttr.setArray(true);
    cAttr.setUsesArrayDataBuilder(true);
    cAttr.setStorable(true);
    cAttr.setHidden(true);
    cAttr.addChild(poseName);
    cAttr.addChild(poseGain);
    cAttr.addChild(poseOffset);
    cAttr.addChild(poseEnabled);
    cAttr.addChild(poseMatrix);
    cAttr.addChild(deformationType);

    cAttr.addChild(deformations);
    addAttribute(poses);
    // now the attribute affects

    attributeAffects(blurSculpt::blurSculptMatrix, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::inTime, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::deformationType, blurSculpt::outputGeom);
    attributeAffects(
        blurSculpt::vectorMovements, blurSculpt::outputGeom
    ); // to be removed eventually
    attributeAffects(blurSculpt::multiVectorMovements, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::poseOffset, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::poseGain, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::poseEnabled, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::poseMatrix, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::frame, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::frameEnabled, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::offset, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::gain, blurSculpt::outputGeom);
    attributeAffects(blurSculpt::smoothNormals, blurSculpt::outputGeom);

    return MStatus::kSuccess;
}

MStatus blurSculpt::deform(
    MDataBlock &block, MItGeometry &iter, const MMatrix & m,
    unsigned int multiIndex
)
//
// Method: deform
//
// Arguments:
//   block		: the datablock of the node
//	 iter		: an iterator for the geometry to be deformed
//   m    		: matrix to transform the point into world space
//	 multiIndex : the index of the geometry that we are deforming
{
    MStatus returnStatus;

    MArrayDataHandle hInput = block.outputArrayValue(input, &returnStatus);
    if (MS::kSuccess != returnStatus)
        return returnStatus;
    returnStatus = hInput.jumpToElement(multiIndex);
    if (MS::kSuccess != returnStatus)
        return returnStatus;

    MObject oInputGeom = hInput.outputValue().child(inputGeom).asMesh();
    MFnMesh fnInputMesh(oInputGeom, &returnStatus);
    if (MS::kSuccess != returnStatus)
        return returnStatus;

    // Envelope data from the base class.
    // The envelope is simply a scale factor.
    //
    MDataHandle envData = block.inputValue(envelope, &returnStatus);
    McheckErr(returnStatus, "couldn't get envelope attr") float env =
        envData.asFloat();
    if (env == 0)
        return returnStatus;

    // Get the matrix which is used to define the direction and scale
    // of the blurSculpt.
    //
    MDataHandle matData = block.inputValue(blurSculptMatrix, &returnStatus);
    McheckErr(returnStatus, "couldn't get blurSculptMatrix attr") MMatrix omat =
        matData.asMatrix();
    MMatrix omatinv = omat.inverse();

    MDataHandle timeData = block.inputValue(inTime, &returnStatus);
    McheckErr(returnStatus, "couldn't get inTime attr") MTime theTime =
        timeData.asTime();
    double theTime_value = theTime.value();

    MDataHandle smoothNormalsData =
        block.inputValue(smoothNormals, &returnStatus);
    McheckErr(returnStatus, "couldn't get smoothNormals attr")
        //	bool useSmoothNormals = smoothNormalsData.asBool();
        int smoothNormalsRepeat = smoothNormalsData.asInt();

    // check if we are in an older version of the plugin
    // it didn't have multi-geometries deformations
    MDataHandle useMultiVectorMovementData =
        block.inputValue(useMultiVectorMovement, &returnStatus);
    McheckErr(
        returnStatus, "couldn't get useMultiVectorMovement attr"
    ) bool usingMultiGeometrisStorage = useMultiVectorMovementData.asBool();

    // READ IN ".uvSet" DATA:
    MDataHandle uvSetDataHandle = block.inputValue(uvSet);
    MString theUVSet = uvSetDataHandle.asString();
    bool isUvSet(false);

    int nbVertices = fnInputMesh.numVertices();
    MPointArray theVerticesSum(nbVertices);
    MArrayDataHandle posesHandle = block.inputValue(poses, &returnStatus);
    if (MS::kSuccess != returnStatus) {
        std::cout << "Error getting deformationFrameHandle " << multiIndex
                  << endl;
        return MS::kFailure;
    }

    unsigned int nbPoses = posesHandle.elementCount();
    unsigned int nbDeformations;
    MDataHandle poseInputVal, poseNameHandle, poseGainHandle, poseOffsetHandle,
        poseEnabledHandle;
    MDataHandle deformationTypeData;
    MString thePoseName;

    size_t nbConn = connectedVerticesMultiFlat.size();
    bool computePairVerts = false;
    if (multiIndex >= nbConn) {
        computePairVerts = true;
    }
    else {
        auto myPair = connectedVerticesMultiFlat[multiIndex];
        std::vector<int> connectedVerticesFlat = myPair.first;
        std::vector<int> connectedVerticesIndicesFlat = myPair.second;
        if (connectedVerticesFlat.size() == 0 ||
            connectedVerticesIndicesFlat.size() == 0) {
            computePairVerts = true;
        }
    }
    if (computePairVerts) {
        if (connectedVerticesMultiFlat.size() <
            (multiIndex + 1)) { // resize the array
            normalsVertsIdsMULTI.resize(multiIndex + 1);
            tangentsVertsIdsMULTI.resize(multiIndex + 1);
            connectedVerticesMultiFlat.resize(multiIndex + 1);
            connectedFacesMultiFlat.resize(multiIndex + 1);
        }
        std::vector<int> connectedVerticesFlat; // a flat array of all vertices
        std::vector<int> connectedVerticesIndicesFlat; // the indices of where
                                                       // to start in array
        connectedVerticesIndicesFlat.resize(nbVertices + 1);

        std::vector<int> connectedFacesFlat; // a flat array of all Faces
        std::vector<int>
            connectedFacesIndicesFlat; // the indices of where to start in array
        connectedFacesIndicesFlat.resize(nbVertices + 1);

        MItMeshVertex vertexIter(oInputGeom);
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

            int nbConnFaces = surroundingFaces.length();
            connectedFacesIndicesFlat[vtxIndex] = sumConnectedFaces;
            for (int k = 0; k < nbConnFaces; ++k)
                connectedFacesFlat.push_back(surroundingFaces[k]);
            sumConnectedFaces += nbConnFaces;
        }
        connectedVerticesIndicesFlat[nbVertices] =
            sumConnectedVertices; // for the  + 1
        connectedFacesIndicesFlat[nbVertices] =
            sumConnectedFaces; // for the  + 1
        connectedVerticesMultiFlat[multiIndex] =
            std::make_pair(connectedVerticesFlat, connectedVerticesIndicesFlat);
        connectedFacesMultiFlat[multiIndex] =
            std::make_pair(connectedFacesFlat, connectedFacesIndicesFlat);

        // ------------------- get the normals IDs ---------------------------
        std::vector<int> normalVerticesFlat; // a flat array of all vertices
        std::vector<int>
            normalVerticesIndicesFlat; // the indices of where to start in array
        std::vector<int> tangentVerticesFlat; // a flat array of all vertices
        std::vector<int> tangentVerticesIndicesFlat; // the indices of where to
                                                     // start in array

        getVertsNormalsTangents(
            oInputGeom, fnInputMesh, normalVerticesFlat,
            normalVerticesIndicesFlat, tangentVerticesFlat,
            tangentVerticesIndicesFlat
        );

        // now flatten them and then Store them -------------------------------
        normalsVertsIdsMULTI[multiIndex] =
            std::make_pair(normalVerticesFlat, normalVerticesIndicesFlat);
        tangentsVertsIdsMULTI[multiIndex] =
            std::make_pair(tangentVerticesFlat, tangentVerticesIndicesFlat);
    }
    // ---  prepare for normals ------------------------
    MFloatVectorArray normals(nbVertices);  // will be resized later
    MFloatVectorArray tangents(nbVertices); // will be resized later
    bool normalsComputed = false;

    // ---  this data is to be build ------------------------
    MFloatVectorArray smoothTangents(nbVertices); // , tangents(nbVertices);
    MFloatVectorArray smoothedNormals(nbVertices);

    MIntArray smoothTangentFound(nbVertices, -1); // init at -1
    MIntArray smoothNormalFound(nbVertices, -1);  // init at -1
    MIntArray matrixNormalFound(nbVertices, -1);  // init at -1
    MMatrixArray vertsMatrices(nbVertices);

    int prevFrameIndex = 0, nextFrameIndex = 0;
    float prevFrame = 0, nextFrame = 0;
    bool hasPrevFrame = false, hasNextFrame = false;
    float prevMult = 0., nextMult = 0., multiplier = 0.;
    int deformType;
    float poseGainValue, poseOffsetValue, theFrame;
    MDataHandle deformationFrameHandle, frameEnabledHandle, frameHandle;

    // -------------------- start transfer of the
    // attributes-------------------------------
    if (!usingMultiGeometrisStorage && multiIndex == 0) {
        // transfer for all the poses
        for (unsigned int poseIndex = 0; poseIndex < nbPoses; poseIndex++) {
            poseInputVal = posesHandle.inputValue(&returnStatus);
            MArrayDataHandle deformationsHandle =
                poseInputVal.child(deformations);
            MDataHandle vectorHandle;
            // transfer for all the deformations
            nbDeformations = deformationsHandle.elementCount();
            for (unsigned int deformIndex = 0; deformIndex < nbDeformations;
                 deformIndex++) {
                // access the frame
                deformationFrameHandle =
                    deformationsHandle.inputValue(&returnStatus);

                MArrayDataHandle vectorMovementsHandle =
                    deformationFrameHandle.child(vectorMovements);
                int nbVectorMvts = vectorMovementsHandle.elementCount();

                // get access to the new form of storing elements
                // ----------------
                MArrayDataHandle storedVectorsHandle =
                    deformationFrameHandle.child(storedVectors);
                MArrayDataBuilder array_builder =
                    storedVectorsHandle.builder(&returnStatus);
                MDataHandle element_hdl = array_builder.addElement(
                    0, &returnStatus
                ); // first element, we only transfer to the first elem in the
                   // array
                MDataHandle child = element_hdl.child(multiVectorMovements
                ); // storedVectors[0].multiVectorMovements

                MArrayDataHandle multiVectorMovementsHandle(
                    child, &returnStatus
                ); // get the handle
                MArrayDataBuilder mvt_builder =
                    multiVectorMovementsHandle.builder(&returnStatus
                    ); // get the builder array

                std::vector<int> toRemove;
                for (int vectorIndex = 0; vectorIndex < nbVectorMvts;
                     vectorIndex++) {
                    vectorMovementsHandle.jumpToArrayElement(vectorIndex);
                    int theVertexNumber = vectorMovementsHandle.elementIndex();
                    vectorHandle =
                        vectorMovementsHandle.inputValue(&returnStatus);
                    float3 &vtxValue =
                        vectorHandle.asFloat3(); // we got the value
                    // now set in the new handle -----------------
                    MDataHandle element_hdl = mvt_builder.addElement(
                        theVertexNumber, &returnStatus
                    ); // weightList[i]
                    element_hdl.set3Float(
                        vtxValue[0], vtxValue[1], vtxValue[2]
                    );
                    // for later remove ----
                    toRemove.push_back(theVertexNumber);
                }
                // set the correct Handle  ----------------------
                multiVectorMovementsHandle.set(mvt_builder);
                storedVectorsHandle.set(array_builder);

                // clear the array ----------------------
                MArrayDataBuilder vectorMovementsBuilder =
                    vectorMovementsHandle.builder();
                for (int el : toRemove)
                    vectorMovementsBuilder.removeElement(el);

                // move to next deformation ----------------------
                deformationsHandle.next();
            }
            // move to next pose
            posesHandle.next();
        }
        // set true so we don't do it again
        useMultiVectorMovementData.set(true);
    }

    // -------------------- do the actual computation
    // -------------------------------
    for (unsigned int poseIndex = 0; poseIndex < nbPoses; poseIndex++) {
        // use this method for arrays that are sparse
        poseInputVal = posesHandle.inputValue(&returnStatus);
        if (MS::kSuccess != returnStatus) {
            std::cout << "Error getting poseInputVal  [" << multiIndex
                      << "] poseIndex [" << poseIndex << "]" << endl;
            continue;
        }

        // check if we need to compute normals
        deformationTypeData = poseInputVal.child(deformationType);
        deformType = deformationTypeData.asInt();

        if (!normalsComputed &&
            deformType != 0) { // HERE we compute the normals  if need be
            normalsComputed = true;
            MGlobal::displayInfo("\n\n compute normals \n\n");

            fnInputMesh.getVertexNormals(false, normals, MSpace::kWorld);

            auto myPair = connectedVerticesMultiFlat[multiIndex];
            std::vector<int> connectedVerticesFlat = myPair.first;
            std::vector<int> connectedVerticesIndicesFlat = myPair.second;

            MItMeshVertex vertexIter(oInputGeom);
            for (int theVertexNumber = 0; theVertexNumber < nbVertices;
                 ++theVertexNumber) {
                MVector tangent =
                    getVertexTangent(fnInputMesh, vertexIter, theVertexNumber);
                tangents.set(tangent, theVertexNumber);
            }
            for (int it = 0; it < smoothNormalsRepeat; ++it) {
                for (int theVertexNumber = 0; theVertexNumber < nbVertices;
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

        poseEnabledHandle = poseInputVal.child(poseEnabled);
        bool isPoseEnabled = poseEnabledHandle.asBool();
        if (isPoseEnabled) {
            deformationTypeData = poseInputVal.child(deformationType);
            deformType = deformationTypeData.asInt();

            poseGainHandle = poseInputVal.child(poseGain);
            poseGainValue = poseGainHandle.asFloat();

            poseOffsetHandle = poseInputVal.child(poseOffset);
            poseOffsetValue = poseOffsetHandle.asFloat();

            MArrayDataHandle deformationsHandle =
                poseInputVal.child(deformations);
            nbDeformations = deformationsHandle.elementCount();
            prevFrameIndex = 0;
            nextFrameIndex = 0;
            prevFrame = 0;
            nextFrame = 0;
            hasPrevFrame = false;
            hasNextFrame = false;
            // check the frames in between
            for (unsigned int deformIndex = 0; deformIndex < nbDeformations;
                 deformIndex++) {
                deformationFrameHandle =
                    deformationsHandle.inputValue(&returnStatus);
                if (MS::kSuccess != returnStatus) {
                    std::cout << "Error getting deformationFrameHandle  ["
                              << multiIndex << "] poseIndex [" << poseIndex
                              << "] deformIndex [" << deformIndex << "]"
                              << endl;
                    continue;
                }

                frameEnabledHandle = deformationFrameHandle.child(frameEnabled);
                bool isFrameEnabled = frameEnabledHandle.asBool();

                if (isFrameEnabled) {
                    frameHandle = deformationFrameHandle.child(frame);
                    theFrame = frameHandle.asFloat();
                    if (theFrame < theTime_value) {
                        if ((!hasPrevFrame) || (theFrame > prevFrame)) {
                            hasPrevFrame = true;
                            prevFrameIndex = deformIndex;
                            prevFrame = theFrame;
                        }
                    }
                    else if (theFrame > theTime_value) {
                        if ((!hasNextFrame) || (theFrame < nextFrame)) {
                            hasNextFrame = true;
                            nextFrameIndex = deformIndex;
                            nextFrame = theFrame;
                        }
                    }
                    else if (theFrame == theTime_value) { // equality
                        hasPrevFrame = true;
                        hasNextFrame = false;
                        prevFrameIndex = deformIndex;
                        prevFrame = theFrame;
                        break;
                    }
                }
                deformationsHandle.next();
            }
            // get the frames multiplication
            prevMult = 0.;
            nextMult = 0.;
            if (hasPrevFrame)
                prevMult = 1.;
            if (hasNextFrame)
                nextMult = 1.;
            if (hasPrevFrame && hasNextFrame) {
                nextMult = float(theTime_value - prevFrame) /
                           float(nextFrame - prevFrame);
                prevMult = float(1. - nextMult);
            }
            MDataHandle poseMatrixData = poseInputVal.child(poseMatrix);
            MMatrix poseMat = poseMatrixData.asMatrix();
            MPoint matPoint = MPoint(0, 0, 0) * poseMat;
            if (hasPrevFrame) {
                deformationsHandle.jumpToArrayElement(prevFrameIndex);

                sumDeformation(
                    multiIndex,
                    deformationsHandle, // the current handle of the deformation
                    fnInputMesh, poseGainValue, poseOffsetValue,
                    prevMult, // the pose multiplication of gain and value
                    poseMat, matPoint, deformType, smoothTangentFound,
                    smoothNormalFound,
                    matrixNormalFound, // if we already have the tangets or not
                    normals, smoothedNormals, tangents,
                    smoothTangents, // the values of tangents and normals
                    vertsMatrices,
                    theVerticesSum
                ); // the output array to fill
            }
            if (hasNextFrame) {
                deformationsHandle.jumpToArrayElement(nextFrameIndex);

                sumDeformation(
                    multiIndex,
                    deformationsHandle, // the current handle of the deformation
                    fnInputMesh, poseGainValue, poseOffsetValue,
                    nextMult, // the pose multiplication of gain and value
                    poseMat, matPoint, deformType, smoothTangentFound,
                    smoothNormalFound,
                    matrixNormalFound, // if we already have the tangets or not
                    normals, smoothedNormals, tangents,
                    smoothTangents, // the values of tangents and normals
                    vertsMatrices,
                    theVerticesSum
                ); // the output array to fill
            }
        }
        posesHandle.next();
    }
    MPoint pt, resPos, toset;
    float weight;
    for (; !iter.isDone(); iter.next()) {
        int theindex = iter.index();
        pt = iter.position();
        weight = weightValue(block, multiIndex, theindex);
        resPos = (pt + theVerticesSum[theindex]) * omat;
        toset = double(env * weight) * resPos + double(1. - env * weight) * pt;
        iter.setPosition(toset);
    }
    return MStatus::kSuccess;
}

/* override */
MObject &blurSculpt::accessoryAttribute() const
//
//	Description:
//	  This method returns a the attribute to which an accessory
//    shape is connected. If the accessory shape is deleted, the deformer
//	  node will automatically be deleted.
//
//    This method is optional.
//
{
    return blurSculpt::blurSculptMatrix;
}

/* override */
MStatus blurSculpt::accessoryNodeSetup(MDagModifier &cmd)
//
//	Description:
//		This method is called when the deformer is created by the
//		"deformer" command. You can add to the cmds in the MDagModifier
//		cmd in order to hook up any additional nodes that your node
//needs 		to operate.
//
//		In this example, we create a locator and attach its matrix
//attribute 		to the matrix input on the blurSculpt node. The locator is used to
//		set the direction and scale of the random field.
//
//	Description:
//		This method is optional.
//
{
    MStatus result;

    //- Connect time1 node with time of node
    MSelectionList selList;

    MObject timeNode;
    MGlobal::getSelectionListByName(MString("time1"), selList);
    selList.getDependNode(0, timeNode);
    selList.clear();

    MFnDependencyNode fnTimeNode(timeNode);
    MObject timeAttr = fnTimeNode.attribute(MString("outTime"), &result);
    cmd.connect(timeNode, timeAttr, this->thisMObject(), blurSculpt::inTime);

    return result;
}
