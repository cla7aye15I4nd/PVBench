#!/bin/bash -eu
autoreconf -fi
./configure
make -j16
make test