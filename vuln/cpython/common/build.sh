#!/bin/bash -eu
./configure --without-pymalloc
ASAN_OPTIONS=detect_leaks=0 make -j$(nproc)
test -f python
