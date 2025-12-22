#!/bin/bash -eu
./buildconf
./configure
make -j$(nproc)
test -f sapi/cli/php
test -f sapi/phpdbg/phpdbg
