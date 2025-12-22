#!/bin/bash -eu
export CFLAGS="-fsanitize=address,undefined"
export CXXFLAGS="-fsanitize=address,undefined"
export LDFLAGS="-fsanitize=address,undefined"
sed -i 's/assertEquals/assertEqual/g' tests/tiff_test/test_tag_compare.py
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$(pwd)/exiv2-build
make -j$(nproc)
make install
make tests