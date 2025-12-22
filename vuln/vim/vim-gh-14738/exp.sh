#!/bin/bash -eu
./src/xxd/xxd -Ralways -g1 -c256 -d -o 9223372036854775808 $1
