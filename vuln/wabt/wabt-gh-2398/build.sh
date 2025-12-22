#!/bin/bash -eu
mkdir -p build
cd build
cmake ..
make -j32
test -f wasm-interp
