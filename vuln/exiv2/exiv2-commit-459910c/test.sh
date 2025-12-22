#!/bin/bash -eu
export CC="gcc-9"
export CXX="g++-9"
sed -i 's/assertEquals/assertEqual/g' tests/tiff_test/test_tag_compare.py
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$(pwd)/exiv2-build
make -j$(nproc)
make install
flock /tmp/make_test.lock -c "make test"