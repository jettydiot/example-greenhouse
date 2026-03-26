cmake_minimum_required(VERSION 3.16)

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/jettyd/CMakeLists.txt")
    message(FATAL_ERROR "\n\n  jettyd SDK not found. Run:\n    make setup\n\n")
endif()

set(EXTRA_COMPONENT_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/jettyd
    ${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/drivers/dht22
    ${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/drivers/soil_moisture
    ${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/drivers/relay
    ${CMAKE_CURRENT_SOURCE_DIR}/jettyd-sdk/drivers/led
)

# Auto-delete sdkconfig if sdkconfig.defaults is newer
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/sdkconfig" AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/sdkconfig.defaults")
    file(TIMESTAMP "${CMAKE_CURRENT_SOURCE_DIR}/sdkconfig" TS_CONFIG)
    file(TIMESTAMP "${CMAKE_CURRENT_SOURCE_DIR}/sdkconfig.defaults" TS_DEFAULTS)
    if(TS_DEFAULTS IS_NEWER_THAN TS_CONFIG)
        message(STATUS "sdkconfig.defaults is newer — deleting stale sdkconfig")
        file(REMOVE "${CMAKE_CURRENT_SOURCE_DIR}/sdkconfig")
    endif()
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(greenhouse-monitor)
