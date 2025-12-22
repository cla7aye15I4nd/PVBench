#!/bin/bash -eu
export CFLAGS="-include stdint.h ${CFLAGS:-}"
export CXXFLAGS="-include cstdint ${CXXFLAGS:-}"
cmake -S . -B build -G Ninja
cmake --build build -j 16
test -f build/bin/hermes