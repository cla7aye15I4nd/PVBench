#!/bin/bash -eu
./build/bin/mlir-opt $1 -test-lower-to-llvm
