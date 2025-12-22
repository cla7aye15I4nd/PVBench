#!/bin/bash -eu

rsync -a /v8-dependencies/v8-regress-1428034/ .

gn gen out/debug_asan --args='
    is_debug=true
    is_asan=true
    is_lsan=true
    v8_enable_backtrace=true
    is_component_build=false
    symbol_level=2
'

ninja -C out/debug_asan -j8 d8
test -f out/debug_asan/d8