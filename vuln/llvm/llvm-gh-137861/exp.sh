#!/bin/bash -eu
./build/bin/clang -x c -ferror-limit=100 $1
