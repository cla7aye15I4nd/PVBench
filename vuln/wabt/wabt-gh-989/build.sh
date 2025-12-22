#!/bin/bash -eu
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j32
test -f wat2wasm
