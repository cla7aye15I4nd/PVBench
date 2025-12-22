#!/bin/bash
./autogen.sh
./configure --prefix=$PWD/install
make -j8
make install
