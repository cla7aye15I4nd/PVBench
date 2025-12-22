#!/bin/bash -eu
make -j$(nproc)
test -f build/qjs
