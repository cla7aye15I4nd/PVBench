#!/bin/bash -eu
export CXXFLAGS="-include stdexcept ${CXXFLAGS:-}"
cmake -S . -B build -G Ninja
cmake --build build -j 16
test -f build/bin/hermes