#!/bin/bash -eu
export CFLAGS="-include stdint.h ${CFLAGS:-}"
export CXXFLAGS="-include cstdint ${CXXFLAGS:-}"
utils/build/configure.py
cd build
ninja -j 16
test -f bin/hermes