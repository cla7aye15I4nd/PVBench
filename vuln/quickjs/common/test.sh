#!/bin/bash -eu
make BUILD_TYPE=RelWithDebInfo CONFIG_ASAN=ON CONFIG_UBSAN=ON -j$(nproc)
make stats -j$(nproc)
make test -j$(nproc)
make test262 -j$(nproc)
