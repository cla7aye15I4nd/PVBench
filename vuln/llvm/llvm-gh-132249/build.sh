#!/bin/bash -eu
mkdir -p build && cd build
cmake -G Ninja \
	-DCMAKE_BUILD_TYPE=Debug \
	-DLLVM_ENABLE_PROJECTS="clang" \
	-DLLVM_TARGETS_TO_BUILD="X86" \
	-DLLVM_BUILD_TESTS=OFF \
	../llvm
ninja -j16 clang
test -f bin/clang++
