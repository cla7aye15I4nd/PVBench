#!/bin/bash -eu

mkdir -p build
cd build
cmake .. \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=Debug \
    -DLEMON_EXECUTABLE=/usr/bin/lemon \
    -DENABLE_ASAN=1 \
    -DENABLE_WERROR=OFF

ninja -j16