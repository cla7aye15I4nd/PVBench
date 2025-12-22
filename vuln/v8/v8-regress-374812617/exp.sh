#!/bin/bash -eu

out/debug_asan/d8 \
    --expose-gc \
    --trace-gc-object-stats \
    "$1"