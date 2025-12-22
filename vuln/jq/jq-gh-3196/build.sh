#!/bin/bash -eu

export CXX=${CXX:-clang++}
export CXXFLAGS=${CXXFLAGS:-"-O1 -fno-omit-frame-pointer -gline-tables-only \
        -Wno-error=enum-constexpr-conversion \
        -Wno-error=incompatible-function-pointer-types \
        -Wno-error=int-conversion \
        -Wno-error=deprecated-declarations \
        -Wno-error=implicit-function-declaration \
        -Wno-error=implicit-int \
        -Wno-error=vla-cxx-extension \
        -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION \
        -fsanitize=address -fsanitize-address-use-after-scope"}
export LIB_FUZZING_ENGINE=${LIB_FUZZING_ENGINE:--fsanitize=fuzzer}

autoreconf -fi
./configure --with-oniguruma=builtin
make -j16

$CXX $CXXFLAGS $LIB_FUZZING_ENGINE ./tests/jq_fuzz_fixed.cpp \
    -I./src \
    ./.libs/libjq.a ./vendor/oniguruma/src/.libs/libonig.a \
    -o build/jq_fuzz_fixed -I./src

test -f build/jq_fuzz_fixed
