#!/bin/bash -eu

out/debug_asan/d8 \
    --reuse-scope-infos \
    --expose-gc \
    --stress-flush-code \
    "$1"