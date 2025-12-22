#!/bin/bash -eu

out/debug_asan/d8 \
    --allow-natives-syntax \
    --turboshaft \
    --turboshaft-assert-types \
    "$1"