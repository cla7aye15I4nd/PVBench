#!/bin/bash -eu
export CFLAGS="-fsanitize=address"
export CXXFLAGS="-fsanitize=address"
export LDFLAGS="-fsanitize=address"
export ASAN_OPTIONS="detect_leaks=0"
HDF5_REPO_PATH=$(pwd)

mkdir build

pushd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=$HDF5_REPO_PATH/install \
    -DBUILD_SHARED_LIBS=ON \
    -DHDF5_BUILD_TOOLS=ON \
    -DHDF5_BUILD_EXAMPLES=OFF \
    -DHDF5_BUILD_TESTS=OFF

make -j16
make install
make test ARGS="-j16"
popd
