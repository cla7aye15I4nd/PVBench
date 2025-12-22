#!/bin/bash
rm ./test/errors/cdata.xml
./autogen.sh
./configure --prefix=$PWD/install --with-zlib --with-lzma --with-schematron --disable-shared --without-python
make -j8
make install
make check -j8