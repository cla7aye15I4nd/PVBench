#!/bin/bash -eu
autoreconf -fi
./configure --with-oniguruma=builtin
make -j16
make check