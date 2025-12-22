#!/bin/bash -eu
./configure --with-pydebug
ASAN_OPTIONS=detect_leaks=0 make -j$(nproc)
test -f python