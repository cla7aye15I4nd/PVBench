#!/bin/bash -eu

out/debug_asan/d8 \
    --stress-lazy-source-positions \
    "$1"