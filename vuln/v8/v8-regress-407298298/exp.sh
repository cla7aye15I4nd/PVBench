#!/bin/bash -eu

out/debug_asan/d8 \
    --no-liftoff \
    --experimental-wasm-jspi \
    "$1"