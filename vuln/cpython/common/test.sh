#!/bin/bash -eu
./configure --without-pymalloc --with-pydebug
make -j$(nproc)
make test -j$(nproc)
