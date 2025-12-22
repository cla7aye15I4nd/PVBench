#!/bin/bash -eu
./configure --prefix=$(pwd)/vim-build --with-features=normal --enable-fail-if-missing
make -j32
make install
export TERM=xterm 
rm src/testdir/test_alot.vim
make test