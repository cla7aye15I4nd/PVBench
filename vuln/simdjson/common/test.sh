#!/bin/bash -eu
mkdir -p build
cd build

export CXX=/workspace/cold/compiler/d++
export CC=/workspace/cold/compiler/dcc
cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DSIMDJSON_DEVELOPER_MODE=ON \
    -DBUILD_SHARED_LIBS=OFF \
    -DSIMDJSON_ENABLE_FUZZING=ON \
    -DSIMDJSON_COMPETITION=OFF \
    -DSIMDJSON_FUZZ_LINKMAIN=OFF \
    -DSIMDJSON_GOOGLE_BENCHMARKS=OFF \
    -DSIMDJSON_DISABLE_DEPRECATED_API=ON \
    -DSIMDJSON_FUZZ_LDFLAGS=-fsanitize=fuzzer

cmake --build . --target all_fuzzers
make -j16 ondemand_basictests
make -j16 amalgamate_demo
make -j16 amalgamate_demo_direct_from_repository
make -j16 numberparsingcheck
make -j16 stringparsingcheck
make -j16 random_string_number_tests
make -j16 basictests
make -j16 minify_tests
make -j16 document_stream_tests
make -j16 document_tests
make -j16 errortests
make -j16 integer_tests
make -j16 jsoncheck
make -j16 minefieldcheck
make -j16 parse_many_test
make -j16 pointercheck
make -j16 extracting_values_example
make -j16 unicode_tests
make -j16 padded_string_tests
make -j16 checkimplementation
make -j16 json2json
make -j16 ondemand_basictests
ctest -j16 -E "(checkperf|testjson2json)"