#!/bin/bash -eu
./build/bin/opt -passes=loop-vectorize -slp-threshold=-99999 -force-vector-width=4 $1