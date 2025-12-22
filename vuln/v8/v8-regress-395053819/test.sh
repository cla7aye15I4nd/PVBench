#!/bin/bash -eu

rsync -a /v8-dependencies/v8-regress-395053819/ .

NINJA_PARALLEL_JOBS=4 tools/dev/gm.py x64.release.d8

python3.11 tools/run-tests.py \
    --outdir=out/x64.release \
    -j16 \
    mjsunit/regress/*