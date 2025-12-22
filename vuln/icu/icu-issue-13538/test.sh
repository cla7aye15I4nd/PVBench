#!/bin/bash -eu
export CC=clang
export CXX=clang++
export CFLAGS="-fsanitize=address"
export CXXFLAGS="-fsanitize=address"
export LDFLAGS="-fsanitize=address"
export ASAN_OPTIONS="detect_leaks=0"
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install
make check -j32