#!/bin/bash -eu
export ASAN_OPTIONS=detect_leaks=0,allocator_may_return_null=1
TERM=xterm ./python $1