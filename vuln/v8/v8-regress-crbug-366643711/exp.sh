#!/bin/bash -eu

out/debug_asan/d8 \
    --harmony-struct \
    --allow-natives-syntax \
    "$1"