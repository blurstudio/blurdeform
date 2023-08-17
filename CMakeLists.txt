cmake_minimum_required(VERSION 3.16)

project(blurPostDeform)

set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)
set(CMAKE_CXX_STANDARD 14)
set(MAYA_VERSION 2020 CACHE STRING "Maya version")

set_property(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY VS_STARTUP_PROJECT ${PROJECT_NAME})
find_package(Maya REQUIRED)
find_package(OpenGL REQUIRED)

if (WIN32)
    set(COMPILE_FLAGS "/arch:AVX")
else()
    set(COMPILE_FLAGS "-mavx")
endif()

set(SOURCE_FILES
    "src/blurPostDeformPlugin.cpp" 
    "src/blurPostDeformNode.cpp" 
    "src/blurPostDeformNode.h" 
    "src/blurPostDeformCmd.cpp" 
    "src/blurPostDeformCmd.h" 
    "src/common.cpp"
    "src/common.h"
    "src/setOverloads.h"
)

add_library(${PROJECT_NAME} SHARED ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} PRIVATE Maya::Maya)
target_include_directories(${PROJECT_NAME} PRIVATE Maya::Maya)
target_compile_options(${PROJECT_NAME} PRIVATE ${COMPILE_FLAGS})

MAYA_PLUGIN(${PROJECT_NAME})
