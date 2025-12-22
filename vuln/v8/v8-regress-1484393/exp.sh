#!/bin/bash -eu

out/debug_asan/d8 \
    --no-liftoff \
    "$1"