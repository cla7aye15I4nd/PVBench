#!/bin/bash -eu
export CC=${CC:-clang}
export CXX=${CXX:-clang++}
export CFLAGS="-fsanitize=address -g -O1"
export LDFLAGS="-fsanitize=address"

autoreconf -fi
CFLAGS="$CFLAGS" LDFLAGS="$LDFLAGS" ./configure
make -j16

HTSLIB_ABS_PATH="$(pwd)"
cd /samtools/
make clean
autoreconf -fi
CFLAGS="$CFLAGS" LDFLAGS="$LDFLAGS" ./configure  --with-htslib="$HTSLIB_ABS_PATH"
cd /samtools/
make -j16