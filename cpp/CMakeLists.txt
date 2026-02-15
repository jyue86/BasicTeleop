# TELEOP/cpp/CMakeLists.txt

# Specify minimum required CMake version
cmake_minimum_required(VERSION 3.20)

# Define the project name
project(teleop_hello_world CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

# Find the installed Holoscan SDK package.
# The PATHS variable provides hints on where to look, especially useful if
# the SDK was installed to a non-standard location like /opt/nvidia/holoscan
# which is common for Debian packages.
find_package(holoscan REQUIRED CONFIG
    PATHS "/opt/nvidia/holoscan"
)
find_package(fastrtps REQUIRED)
find_package(fastcdr REQUIRED)
find_package(realsense2 REQUIRED)
set(THIRD_PARTY_LIBS ${realsense2_LIBRARY})

# Define the C++ executable.
# Assuming your source file is in a 'src' subdirectory (TELEOP/cpp/src/hello_world.cpp)
add_executable(hello_world
    src/hello_world.cpp
)
add_executable(ping
    src/ping.cpp
)
add_executable(realsense
    src/realsense.cpp
    src/realsense.hpp
)
add_executable(holoviz_camera
    src/holoviz_camera_app.cpp
)
add_executable(distributed_app
    src/distributed_app.cpp 
)

# Link the executable against the necessary Holoscan libraries.
# holoscan::core is the primary target for all Holoscan applications.
target_link_libraries(hello_world 
    PRIVATE
    holoscan::core
)
target_link_libraries(ping 
    PRIVATE
    holoscan::core
    holoscan::ops::ping_tx
    holoscan::ops::ping_rx
)
target_link_libraries(realsense
    PRIVATE
    holoscan::core
    holoscan::ops::holoviz
    ${THIRD_PARTY_LIBS}
)
target_link_libraries(holoviz_camera
    PRIVATE
    holoscan::core
    holoscan::ops::holoviz
)
target_link_libraries(distributed_app
    PRIVATE
    holoscan::core
    holoscan::ops::ping_tx
    holoscan::ops::ping_rx
)

# OPTIONAL: Set RPATH to ensure the executable finds the shared libraries (like libholoscan_core.so)
# without relying on LD_LIBRARY_PATH, especially if you move the executable later.
# This assumes the Holoscan libraries are located relative to the executable's install directory.
set_target_properties(hello_world PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
)
set_target_properties(ping PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
)