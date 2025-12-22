#!/bin/bash
./autogen.sh
./configure --prefix=$PWD/install --with-zlib --with-lzma --with-schematron --disable-shared
make -j8
make install

test -f ./xmllint
