#!/bin/bash -eu
export CC="gcc-9"
export CXX="g++-9"
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$(pwd)/exiv2-build
make -j$(nproc)
make install
test -f ./bin/exiv2
