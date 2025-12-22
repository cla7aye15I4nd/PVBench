#!/bin/bash -eu

cmake -S . -B build-dir \
    -DCMAKE_INSTALL_PREFIX=$PWD/install \
    -DJAS_ENABLE_LIBHEIF=1 \
    -DJAS_ENABLE_MULTITHREADING_SUPPORT=0 \
    -DALLOW_IN_SOURCE_BUILD=YES
    
pushd build-dir
make -j16
make install
popd

test -f install/bin/jasper