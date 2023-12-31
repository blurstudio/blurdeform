/*
from chad vernon
*/

#include "common.h"

#include <algorithm>
#include <cassert>
#include <maya/MFnDagNode.h>
#include <maya/MFnMesh.h>
#include <maya/MGlobal.h>
#include <maya/MItMeshVertex.h>
#include <maya/MSelectionList.h>
#include <queue>
#include <set>
#include <utility>

#define NORMALIZATION_INDEX -1

void getVertsNormalsTangents(
    MObject &oInputGeom, MFnMesh &fnInputMesh,
    std::vector<int> &normalVerticesFlat,
    std::vector<int> &normalVerticesNBFlat,
    std::vector<int> &tangentVerticesFlat,
    std::vector<int> &tangentVerticesNBFlat
)
{
    // the normals
    int numFaces = fnInputMesh.numPolygons();
    int nbVertices = fnInputMesh.numVertices();

    std::vector<std::vector<int>>
        normalsVertsIds; // vector of faces Ids normals
    normalsVertsIds.resize(nbVertices);
    std::vector<std::vector<int>>
        tangentsVertsIds; // vector of faces Ids normals
    tangentsVertsIds.resize(nbVertices);

    // get the Data
    MIntArray normalFaceIdCounts, normalsFaceId;
    fnInputMesh.getNormalIds(normalFaceIdCounts, normalsFaceId);

    // get connections from polygons -------------------------
    MItMeshPolygon polyIter(oInputGeom);
    std::vector<MIntArray>
        FaceToVertices; // use by MItMeshVertex getConnectedVertices

    FaceToVertices.resize(numFaces);
    int globalIndexInArrayNormals = 0; // start at zero
    for (int faceTmp = 0; !polyIter.isDone(); polyIter.next(), ++faceTmp) {
        MIntArray surroundingVertices;
        polyIter.getVertices(surroundingVertices);
        int indFace = polyIter.index();

        // CAN BE REMOVED I HOPE ! it is just a test
        int nbNormalsInFace = normalFaceIdCounts[faceTmp];
        if (nbNormalsInFace != surroundingVertices.length()) {
            MGlobal::displayInfo(
                MString("not matching nb verts per face [") +
                surroundingVertices.length() + MString("] in face [") +
                indFace + MString("] ;")
            );
        }
        // end of test ----
        for (int k = 0; k < surroundingVertices.length(); ++k) {
            int indVtx = surroundingVertices[k];
            int indNormal = normalsFaceId[globalIndexInArrayNormals];
            normalsVertsIds[indVtx].push_back(indNormal);
            globalIndexInArrayNormals++;

            int indTangent = fnInputMesh.getTangentId(indFace, indVtx); // not k
            tangentsVertsIds[indVtx].push_back(indTangent);
        }
    }
    // now flatten normals for faster access ----------------------------
    normalVerticesNBFlat.resize(nbVertices);
    int sumNormalVertices = 0;

    for (int indVtx = 0; indVtx < nbVertices; indVtx++) {
        std::vector<int> normalsIds = normalsVertsIds[indVtx];
        for (int normalId : normalsIds)
            normalVerticesFlat.push_back(normalId);
        normalVerticesNBFlat[indVtx] = normalsIds.size();
        ;
    }

    // now flatten tangents for faster access ----------------------------
    tangentVerticesNBFlat.resize(nbVertices);
    int sumTangentVertices = 0;

    for (int indVtx = 0; indVtx < nbVertices; indVtx++) {
        std::vector<int> tangentsIds = tangentsVertsIds[indVtx];
        for (int tangentId : tangentsIds)
            tangentVerticesFlat.push_back(tangentId);
        tangentVerticesNBFlat[indVtx] = tangentsIds.size();
    }
}

MStatus getTheNormalsAndTangents(
    MFnMesh &fnInputMesh, std::vector<int> &normalVerticesFlat,
    std::vector<int> &normalVerticesNBFlat,
    std::vector<int> &tangentVerticesFlat,
    std::vector<int> &tangentVerticesNBFlat, MFloatVectorArray &normals,
    MFloatVectorArray &tangents
)
{

    MStatus returnStatus;
    const float *rawNormals = fnInputMesh.getRawNormals(&returnStatus);
    MFloatVectorArray rawTangents;
    MStatus gettingTangentsStat = fnInputMesh.getTangents(rawTangents);
    if (gettingTangentsStat != MStatus::kSuccess)
        return gettingTangentsStat;

    int nbVertices = fnInputMesh.numVertices();

    int globalNormalIndex = 0;
    int globalTangentIndex = 0;
    for (unsigned int vertexInd = 0; vertexInd < nbVertices; vertexInd++) {
        MFloatVector sumNormals;
        bool firstNormal = true;

        int nbNormals = normalVerticesNBFlat[vertexInd];
        for (int k = 0; k < nbNormals; ++k) {
            int indNormal = normalVerticesFlat[globalNormalIndex];
            globalNormalIndex++;

            MFloatVector theNormal(
                rawNormals[indNormal * 3], rawNormals[indNormal * 3 + 1],
                rawNormals[indNormal * 3 + 2]
            );
            if (firstNormal) {
                sumNormals = theNormal;
                firstNormal = false;
            }
            else
                sumNormals += theNormal;
        }

        sumNormals.normalize();
        normals.set(sumNormals, vertexInd);

        // now tangents -------------------
        MFloatVector sumTangents;
        bool firstTangent = true;
        int nbTangents = tangentVerticesNBFlat[vertexInd];
        for (int k = 0; k < nbTangents; ++k) {
            int indTangent = tangentVerticesFlat[globalTangentIndex];
            globalTangentIndex++;

            MFloatVector theTangent = rawTangents[indTangent];
            if (firstNormal) {
                sumNormals = theTangent;
                firstNormal = false;
                break;
            }
            else
                sumNormals += theTangent;
        }

        sumTangents.normalize();
        tangents.set(sumTangents, vertexInd);
    }
    return returnStatus;
}

void getSmoothedVector(
    int indVtx, MIntArray &smoothVectorFound, MFloatVectorArray &Vectors,
    MFloatVectorArray &smoothedVectors, std::vector<int> &connectedVerticesFlat,
    std::vector<int> &connectedVerticesIndicesFlat
)
{

    MFloatVector sumVector;

    int startIndx = connectedVerticesIndicesFlat[indVtx];
    int endIndx = connectedVerticesIndicesFlat[indVtx + 1];
    for (int k = startIndx; k < endIndx; ++k) {

        int vtxAround = connectedVerticesFlat[k];
        if (k == 0) {
            sumVector = Vectors[vtxAround];
        }
        else {
            sumVector += Vectors[vtxAround];
        }
    }
    // finish --------------
    sumVector.normalize();
    sumVector += Vectors[indVtx];
    sumVector = .5 * sumVector;

    smoothVectorFound.set(1, indVtx);
    smoothedVectors.set(sumVector, indVtx);
}

MVector
getVertexTangent(MFnMesh &fnInputMesh, MItMeshVertex &meshVertIt, int indVtx)
{
    int oldInd;
    meshVertIt.setIndex(indVtx, oldInd);
    MIntArray connectedFaces;
    meshVertIt.getConnectedFaces(connectedFaces);

    return getVertexTangentFromFace(fnInputMesh, connectedFaces, indVtx);
}

MVector getVertexTangentFromFace(
    MFnMesh &fnInputMesh, MIntArray &connectedFaces, int indVtx
)
{
    MVector tangent;
    MVector theTangent;
    for (unsigned int i = 0; i < connectedFaces.length(); i += 3) {
        int theFace = connectedFaces[i];
        fnInputMesh.getFaceVertexTangent(
            theFace, indVtx, theTangent, MSpace::kWorld
        );
        if (i == 0) {
            tangent = theTangent;
            break;
        }
        else {
            tangent += theTangent;
        }
    }
    tangent.normalize();
    return tangent;
}

unsigned int getMStringIndex(MStringArray &myArray, MString &searching)
{
    unsigned int toReturn = -1;
    for (unsigned int element = 0; element < myArray.length(); ++element) {
        if (myArray[element] == searching) {
            toReturn = element;
            break;
        }
    }
    return toReturn;
}
unsigned int GetFreeIndex(MPlug &plug)
{
    MStatus stat;
    unsigned int numElements = plug.numElements(&stat);

    // Look for an empty slot
    unsigned int freeIndex = numElements;
    for (unsigned int element = 0; element < numElements; ++element) {
        MPlug newTargetPlug = plug.elementByPhysicalIndex(element, &stat);
        unsigned int logicalIndex = newTargetPlug.logicalIndex(&stat);
        if (logicalIndex > element) {
            return element;
        }
    }
    return freeIndex;
}

void StartProgress(const MString &title, unsigned int count)
{
    if (MGlobal::mayaState() == MGlobal::kInteractive) {
        MString message = "progressBar -e -bp -ii true -st \"";
        message += title;
        message += "\" -max ";
        message += count;
        message += " $gMainProgressBar;";
        MGlobal::executeCommand(message);
    }
}

void StepProgress(int step)
{
    if (MGlobal::mayaState() == MGlobal::kInteractive) {
        MString message = "progressBar -e -s ";
        message += step;
        message += " $gMainProgressBar;";
        MGlobal::executeCommand(message);
    }
}

bool ProgressCancelled()
{
    if (MGlobal::mayaState() == MGlobal::kInteractive) {
        int cmdResult = 0;
        MGlobal::executeCommand(
            "progressBar -query -isCancelled $gMainProgressBar", cmdResult
        );
        return cmdResult != 0;
    }
    return false;
}

void EndProgress()
{
    if (MGlobal::mayaState() == MGlobal::kInteractive) {
        MGlobal::executeCommand("progressBar -e -ep $gMainProgressBar;");
    }
}

bool IsShapeNode(MDagPath &path)
{
    return path.node().hasFn(MFn::kMesh) ||
           path.node().hasFn(MFn::kNurbsCurve) ||
           path.node().hasFn(MFn::kNurbsSurface);
}

MStatus GetShapeNode(MDagPath &path, bool intermediate)
{
    MStatus status;

    if (IsShapeNode(path)) {
        // Start at the transform so we can honor the intermediate flag.
        path.pop();
    }

    if (path.hasFn(MFn::kTransform)) {
        unsigned int shapeCount = path.childCount();

        for (unsigned int i = 0; i < shapeCount; ++i) {
            status = path.push(path.child(i));
            CHECK_MSTATUS_AND_RETURN_IT(status);
            if (!IsShapeNode(path)) {
                path.pop();
                continue;
            }

            MFnDagNode fnNode(path, &status);
            CHECK_MSTATUS_AND_RETURN_IT(status);
            if ((!fnNode.isIntermediateObject() && !intermediate) ||
                (fnNode.isIntermediateObject() && intermediate)) {
                return MS::kSuccess;
            }
            // Go to the next shape
            path.pop();
        }
    }

    // No valid shape node found.
    return MS::kFailure;
}

MStatus GetDagPath(MString &name, MDagPath &path)
{
    MStatus status;
    MSelectionList list;
    status = MGlobal::getSelectionListByName(name, list);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    status = list.getDagPath(0, path);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    return MS::kSuccess;
}

MStatus DeleteIntermediateObjects(MDagPath &path)
{
    MStatus status;
    MDagPath pathMesh(path);
    while (GetShapeNode(pathMesh, true) == MS::kSuccess) {
        status =
            MGlobal::executeCommand("delete " + pathMesh.partialPathName());
        CHECK_MSTATUS_AND_RETURN_IT(status);
        pathMesh = MDagPath(path);
    }
    return MS::kSuccess;
}

void GetBarycentricCoordinates(
    const MPoint &P, const MPoint &A, const MPoint &B, const MPoint &C,
    BaryCoords &coords
)
{
    // Compute the normal of the triangle
    MVector N = (B - A) ^ (C - A);
    MVector unitN = N.normal();

    // Compute twice area of triangle ABC
    double areaABC = unitN * N;

    if (areaABC == 0.0) {
        // If the triangle is degenerate, just use one of the points.
        coords[0] = 1.0f;
        coords[1] = 0.0f;
        coords[2] = 0.0f;
        return;
    }

    // Compute a
    double areaPBC = unitN * ((B - P) ^ (C - P));
    coords[0] = (float)(areaPBC / areaABC);

    // Compute b
    double areaPCA = unitN * ((C - P) ^ (A - P));
    coords[1] = (float)(areaPCA / areaABC);

    // Compute c
    coords[2] = 1.0f - coords[0] - coords[1];
}

MStatus GetAdjacency(MDagPath &pathMesh, std::vector<std::set<int>> &adjacency)
{
    MStatus status;
    // Get mesh adjacency.  The adjacency will be all vertex ids on the
    // connected faces.
    MItMeshVertex itVert(pathMesh, MObject::kNullObj, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    MFnMesh fnMesh(pathMesh, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    adjacency.resize(itVert.count());
    for (; !itVert.isDone(); itVert.next()) {
        MIntArray faces;
        status = itVert.getConnectedFaces(faces);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        adjacency[itVert.index()].clear();
        // Put the vertex ids in a set to avoid duplicates
        for (unsigned int j = 0; j < faces.length(); ++j) {
            MIntArray vertices;
            fnMesh.getPolygonVertices(faces[j], vertices);
            for (unsigned int k = 0; k < vertices.length(); ++k) {
                if (vertices[k] != itVert.index()) {
                    adjacency[itVert.index()].insert(vertices[k]);
                }
            }
        }
    }
    return MS::kSuccess;
}

/**
  Used in the CrawlSurface function to keep track of where we are crawling.
*/
struct CrawlData {
    MPoint sourcePosition; /**< Where the crawl iteration came from. */
    double crawlDistance;  /**< How far this crawl iteration has traveled. */
    int nextVertex;        /**< Where this crawl iteration should go next. */
};

MStatus CrawlSurface(
    const MPoint &startPoint, const MIntArray &vertexIndices,
    MPointArray &points, double maxDistance,
    std::vector<std::set<int>> &adjacency, std::map<int, double> &distances
)
{
    MStatus status;
    distances[NORMALIZATION_INDEX] = 0.0; // -1 will represent our hit point.
    double minStartDistance = 999999.0;
    int minStartIndex = 0;

    // Instead of a recursive function, which can get pretty slow, we'll use a
    // queue to keep track of where we are going and where we are coming from.
    std::queue<CrawlData> verticesToVisit;
    // Add the initial crawl paths to the queue.
    for (unsigned int i = 0; i < vertexIndices.length(); ++i) {
        double distance = startPoint.distanceTo(points[vertexIndices[i]]);
        // Only crawl to the starting vertices if they are within the radius.
        if (distance <= maxDistance) {
            CrawlData root = {startPoint, distance, vertexIndices[i]};
            verticesToVisit.push(root);
        }
        // Track the minimum start distance in case we need to add the closest
        // vertex below. The minimum must be greater than 0 to make sure we do
        // not use the vertex that is the same as the startPoint which would
        // create an invalid up vector.
        if (distance < minStartDistance && distance > 0.000001) {
            minStartDistance = distance;
            minStartIndex = vertexIndices[i];
        }
    }
    // If we didn't even reach a vertex in the hit face, or the startPoint is
    // equal to a vertex on the face, add the closest vertex so we can calculate
    // a proper up vector
    if (verticesToVisit.size() <= 1) {
        CrawlData root = {startPoint, maxDistance - 0.001, minStartIndex};
        verticesToVisit.push(root);
        distances[minStartIndex] = maxDistance - 0.001;
    }
    while (verticesToVisit.size()) {
        CrawlData next = verticesToVisit.front();
        verticesToVisit.pop();

        // Extract the data out of the crawl struct
        int idx = next.nextVertex;
        MPoint &pt = points[idx];
        MPoint sourcePoint = next.sourcePosition;
        double currentCrawlDistance = next.crawlDistance;

        currentCrawlDistance += sourcePoint.distanceTo(pt);
        if (currentCrawlDistance >= maxDistance) {
            // If this vertex is outside the radius, no need to crawl anymore
            // from that vertex.
            continue;
        }
        double &savedDistance = distances[idx];
        if (currentCrawlDistance <= savedDistance || savedDistance == 0.0) {
            // If this current crawl distance is less then the distance we have
            // saved for this vertex, use this new crawl distance instead.
            savedDistance = currentCrawlDistance;
        }
        else {
            // A smaller distance is already stored so we don't want to crawl
            // from this vertex any further.
            continue;
        }
        // Crawl the adjacent vertices
        std::set<int>::iterator iter;
        for (iter = adjacency[idx].begin(); iter != adjacency[idx].end();
             ++iter) {
            CrawlData data = {pt, currentCrawlDistance, *iter};
            verticesToVisit.push(data);
        }
    }
    assert(distances.size() > 0);

    return MS::kSuccess;
}

bool SampleSort(std::pair<int, double> lhs, std::pair<int, double> rhs)
{
    // Ensure that the normalization sample comes last.
    return (lhs.second < rhs.second) || rhs.first == NORMALIZATION_INDEX;
}

void CalculateSampleWeights(
    const std::map<int, double> &distances, double radius, MIntArray &vertexIds,
    MDoubleArray &weights
)
{

    std::map<int, double>::const_iterator itDistance;
    std::vector<std::pair<int, double>> samples;
    for (itDistance = distances.begin(); itDistance != distances.end();
         itDistance++) {
        double x = itDistance->second;
        double w = 1.0 - (x / radius);
        samples.push_back(std::pair<int, double>(itDistance->first, w));
    }

    // Make the samples a multiple of 4 so we can use fast intrinsics!
    int remainder = 4 - ((samples.size() - 1) % 4);
    if (remainder != 4) {
        for (int i = 0; i < remainder; ++i) {
            samples.push_back(std::pair<int, double>(0, 0.0));
        }
    }

    unsigned int length = (unsigned int)samples.size();
    weights.setLength(length);
    vertexIds.setLength(length);
    std::sort(samples.begin(), samples.end(), SampleSort);
    std::vector<std::pair<int, double>>::iterator iter;
    int ii = 0;
    double sum = 0.0;
    for (iter = samples.begin(); iter != samples.end(); ++iter, ++ii) {
        vertexIds[ii] = (*iter).first;
        weights[ii] = (*iter).second;
        sum += (*iter).second;
    }
    assert(sum > 0.0);
    // Normalize the weights
    for (unsigned int i = 0; i < weights.length(); ++i) {
        weights[i] /= sum;
    }
}

void CreateMatrix(
    const MPoint &origin, const MFloatVector &normal, const MFloatVector &up,
    MMatrix &matrix
)
{
    const MPoint &t = origin;
    const MFloatVector &y = normal;
    MFloatVector x = y ^ up;
    MFloatVector z = x ^ y;
    // Renormalize vectors
    x.normalize();
    z.normalize();
    matrix[0][0] = x.x;
    matrix[0][1] = x.y;
    matrix[0][2] = x.z;
    matrix[0][3] = 0.0;
    matrix[1][0] = y.x;
    matrix[1][1] = y.y;
    matrix[1][2] = y.z;
    matrix[1][3] = 0.0;
    matrix[2][0] = z.x;
    matrix[2][1] = z.y;
    matrix[2][2] = z.z;
    matrix[2][3] = 0.0;
    matrix[3][0] = t.x;
    matrix[3][1] = t.y;
    matrix[3][2] = t.z;
    matrix[3][3] = 1.0;
}

void CalculateBasisComponents(
    const MDoubleArray &weights, const BaryCoords &coords,
    const MIntArray &triangleVertices, const MPointArray &points,
    const MFloatVectorArray &normals, const MIntArray &sampleIds,
    double *alignedStorage, MPoint &origin, MVector &up, MVector &normal
)
{
    // Start with the recreated point and normal using the barycentric
    // coordinates of the hit point.
    unsigned int hitIndex = weights.length() - 1;
#ifdef __AVX__
    __m256d originV = Dot4<MPoint>(
        coords[0], coords[1], coords[2], 0.0, points[triangleVertices[0]],
        points[triangleVertices[1]], points[triangleVertices[2]], MPoint::origin
    );
    __m256d hitNormalV = Dot4<MVector>(
        coords[0], coords[1], coords[2], 0.0, normals[triangleVertices[0]],
        normals[triangleVertices[1]], normals[triangleVertices[2]],
        MVector::zero
    );
    __m256d hitWeightV = _mm256_set1_pd(weights[hitIndex]);
    // Create the barycentric point and normal.
    __m256d normalV = _mm256_mul_pd(hitNormalV, hitWeightV);
    // Then use the weighted adjacent data.
    for (unsigned int j = 0; j < hitIndex; j += 4) {
        __m256d tempNormal = Dot4<MVector>(
            weights[j], weights[j + 1], weights[j + 2], weights[j + 3],
            normals[sampleIds[j]], normals[sampleIds[j + 1]],
            normals[sampleIds[j + 2]], normals[sampleIds[j + 3]]
        );
        normalV = _mm256_add_pd(tempNormal, normalV);
    }

    _mm256_store_pd(alignedStorage, originV);
    origin.x = alignedStorage[0];
    origin.y = alignedStorage[1];
    origin.z = alignedStorage[2];
    _mm256_store_pd(alignedStorage, normalV);
    normal.x = alignedStorage[0];
    normal.y = alignedStorage[1];
    normal.z = alignedStorage[2];

    // Calculate the up vector
    const MPoint &pt1 = points[triangleVertices[0]];
    const MPoint &pt2 = points[triangleVertices[1]];
    __m256d p1 = _mm256_set_pd(pt1.w, pt1.z, pt1.y, pt1.x);
    __m256d p2 = _mm256_set_pd(pt2.w, pt2.z, pt2.y, pt2.x);
    p1 = _mm256_add_pd(p1, p2);
    __m256d half = _mm256_set_pd(0.5, 0.5, 0.5, 0.5);
    p1 = _mm256_mul_pd(p1, half);
    __m256d upV = _mm256_sub_pd(p1, originV);
    _mm256_store_pd(alignedStorage, upV);
    up.x = alignedStorage[0];
    up.y = alignedStorage[1];
    up.z = alignedStorage[2];
#else
    MVector hitNormal;
    // Create the barycentric point and normal.
    for (int i = 0; i < 3; ++i) {
        origin += points[triangleVertices[i]] * coords[i];
        hitNormal += MVector(normals[triangleVertices[i]]) * coords[i];
    }
    // Use crawl data to calculate normal
    normal = hitNormal * weights[hitIndex];
    for (unsigned int j = 0; j < hitIndex; j++) {
        normal += MVector(normals[sampleIds[j]]) * weights[j];
    }

    // Calculate the up vector
    // The triangle vertices are sorted by decreasing barycentric coordinates so
    // the first two are the two closest vertices in the triangle.
    up = ((points[triangleVertices[0]] + points[triangleVertices[1]]) * 0.5) -
         origin;
#endif
    normal.normalize();
    GetValidUp(weights, points, sampleIds, origin, normal, up);
}

void GetValidUp(
    const MDoubleArray &weights, const MPointArray &points,
    const MIntArray &sampleIds, const MPoint &origin, const MVector &normal,
    MVector &up
)
{
    MVector unitUp = up.normal();
    // Adjust up if it's parallel to normal or if it's zero length
    if (abs((unitUp * normal) - 1.0) < 0.001 || up.length() < 0.0001) {
        for (unsigned int j = 0; j < weights.length() - 1; ++j) {
            up -= (points[sampleIds[j]] - origin) * weights[j];
            unitUp = up.normal();
            if (abs((unitUp * normal) - 1.0) > 0.001 && up.length() > 0.0001) {
                // If the up and normal vectors are no longer parallel and the
                // up vector has a length, then we are good to go.
                break;
            }
        }
        up.normalize();
    }
    else {
        up = unitUp;
    }
}
