cmake_minimum_required(VERSION 3.25)

project(Cloak LANGUAGES CXX C)

# ADR-0002 originally pinned Cloak to MSVC/Windows exclusively (see WINDOWS_BUILD.md).
# Native macOS/Linux builds (Clang/GCC) are also supported now; MSVC remains required on Windows.
if(CMAKE_SYSTEM_NAME STREQUAL "Windows" AND NOT MSVC)
    message(FATAL_ERROR "On Windows, Cloak requires MSVC. See WINDOWS_BUILD.md.")
endif()

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Include modules
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(warnings)
include(msvc_options)
include(cloak_add_library)

# Make <cloak/...> angle-bracket includes available to all targets in the tree.
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/include")
include_directories("${CMAKE_CURRENT_SOURCE_DIR}/src")

# Apply global options
cloak_apply_msvc_options()

# Set up testing if this is not a subproject
if(CMAKE_PROJECT_NAME STREQUAL PROJECT_NAME)
    include(CTest)
endif()

# ── Dependencies (vcpkg manifest mode) ──────────────────────────────────────
find_package(unofficial-sodium CONFIG REQUIRED)
# Convenience alias: ev libraries link against "sodium"
if(NOT TARGET sodium)
    add_library(sodium ALIAS unofficial-sodium::sodium)
endif()
find_package(Boost           REQUIRED COMPONENTS program_options)
find_package(unofficial-sqlite3 CONFIG REQUIRED)
find_package(spdlog          CONFIG REQUIRED)
find_package(fmt             CONFIG REQUIRED)
find_package(Catch2          CONFIG REQUIRED)
# ftxui, wil removed: terminal UI replaced by Android app; wil was unused
# protobuf: available but not yet used in Phase 2 (wire format is hand-rolled)
# find_package(protobuf CONFIG REQUIRED)

# Convenience alias: cloak_add_library uses "unofficial::sqlite3::sqlite3".
# No alias needed — that IS the vcpkg target name.

# ── Source directories ────────────────────────────────────────────────────────
add_subdirectory(src/core)
add_subdirectory(src/crypto)
add_subdirectory(src/identity)
add_subdirectory(src/wire)
add_subdirectory(src/store)
add_subdirectory(src/transport)
add_subdirectory(src/session)
# discovery, ui, app removed: replaced by Rust server + Android app
add_subdirectory(src/transfer)
add_subdirectory(src/group)
add_subdirectory(src/relay)

# Installer placeholder
add_custom_target(installer
    COMMAND ${CMAKE_COMMAND} -E echo "WiX MSI installer coming in M1.11"
)
