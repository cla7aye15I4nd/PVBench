#!/bin/bash -eu
export CC=clang
export CXX=clang++
export CFLAGS="-fsanitize=address,undefined"
export CXXFLAGS="-fsanitize=address,undefined"
export LDFLAGS="-fsanitize=address,undefined"
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install
make check -j32