cmake_minimum_required(VERSION 3.15)
project(message_wrapper)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")

# Main library
add_library(message_wrapper_lib SHARED
    src/message_wrapper.cpp
)
target_include_directories(message_wrapper_lib PUBLIC include)
target_include_directories(message_wrapper_lib PUBLIC ../my_lib)

# Google Test (optional)
find_package(GTest)
if(GTest_FOUND)
    add_executable(test_wrapper tests/test_wrapper.cpp src/message_wrapper.cpp)
    target_include_directories(test_wrapper PUBLIC include ../my_lib)
    target_link_libraries(test_wrapper GTest::GTest GTest::Main)
else()
    message(WARNING "GTest not found - skipping tests. Install with: apt-get install libgtest-dev")
endif()

# Python bindings with pybind11 (optional)
find_package(pybind11 CONFIG)
if(pybind11_FOUND)
    pybind11_add_module(message_wrapper src/bindings.cpp src/message_wrapper.cpp)
    target_include_directories(message_wrapper PUBLIC include ../my_lib)
else()
    message(WARNING "pybind11 not found - skipping Python bindings. Install with: pip install pybind11")
endif()
