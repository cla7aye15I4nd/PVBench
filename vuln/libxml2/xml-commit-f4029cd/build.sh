#!/bin/bash
if [ ! -z "${CFLAGS:-}" ]; then
    export CFLAGS="$CFLAGS -fno-sanitize=function,pointer-overflow"
fi

if [ ! -z "${CXXFLAGS:-}" ]; then
    export CXXFLAGS="$CXXFLAGS -fno-sanitize=function,pointer-overflow"
fi

if [ ! -z "${LDFLAGS:-}" ]; then
    export LDFLAGS="$LDFLAGS -fno-sanitize=function,pointer-overflow"
fi

./autogen.sh
./configure --prefix=$PWD/install --with-zlib --with-lzma --with-schematron --disable-shared
make -j8
make install

test -f ./xmllint
