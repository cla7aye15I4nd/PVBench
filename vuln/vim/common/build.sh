#!/bin/bash -eu
./configure --prefix=$(pwd)/vim-build \
    --enable-fail-if-missing \
    --with-features=huge \
    --enable-gui=no
make -j32
make install
test -f src/vim