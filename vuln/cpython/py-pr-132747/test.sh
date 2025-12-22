#!/bin/bash -eu
./configure --with-pydebug
make -j$(nproc)
make test TESTOPTS="-x test_embed" -j$(nproc)
