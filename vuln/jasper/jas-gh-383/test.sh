#!/bin/bash -eu
cmake -S . -B build-dir \
    -DCMAKE_INSTALL_PREFIX=$PWD/install \
    -DALLOW_IN_SOURCE_BUILD=YES
    
pushd build-dir
make -j16
make install
make test
popd
