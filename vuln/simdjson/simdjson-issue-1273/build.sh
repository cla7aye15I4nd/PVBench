#!/bin/bash -eu
export CC=${CC:-/workspace/cold/compiler/dcc}
export CXX=${CXX:-/workspace/cold/compiler/d++}

mkdir -p build
cd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DSIMDJSON_DEVELOPER_MODE=ON \
    -DBUILD_SHARED_LIBS=OFF \
    -DSIMDJSON_ENABLE_FUZZING=On \
    -DSIMDJSON_COMPETITION=Off \
    -DSIMDJSON_FUZZ_LINKMAIN=Off \
    -DSIMDJSON_GOOGLE_BENCHMARKS=Off \
    -DSIMDJSON_DISABLE_DEPRECATED_API=On \
    -DSIMDJSON_FUZZ_LDFLAGS=-fsanitize=fuzzer

cmake --build . --target all_fuzzers
test -f fuzz/fuzz_ondemand