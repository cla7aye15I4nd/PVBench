#!/bin/bash -eu

out/debug_asan/d8 \
    --allow-natives-syntax \
    "$1"