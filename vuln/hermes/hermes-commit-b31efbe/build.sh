#!/bin/bash -eu
cmake -S . -B build -G Ninja
cmake --build build -j 16
test -f build/bin/hermes