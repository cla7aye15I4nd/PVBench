#!/bin/bash -eu
./configure --with-pydebug --without-pymalloc
ASAN_OPTIONS=detect_leaks=0 make -j$(nproc)
test -f python