#!/bin/bash -eu
export CC=/workspace/cold/compiler/dcc
export CXX=/workspace/cold/compiler/d++
export CFLAGS="-fsanitize=address"
export CXXFLAGS="-fsanitize=address"
export LDFLAGS="-fsanitize=address"
export ASAN_OPTIONS="print_stacktrace=1:detect_leaks=0:log_path=logs/asan"
export UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1:log_path=logs/ubsan"
./configure --prefix=$(pwd)/vim-build \
    --enable-fail-if-missing \
    --with-features=huge \
    --enable-gui=no
make -j32
make install

mkdir -p logs
export TERM=xterm 
cd src/testdir
if ls test_vim9*.vim >/dev/null 2>&1; then make test_vim9; fi
if [ -f test_cmdline.vim ]; then make test_cmdline; fi
if [ -f test_crash.vim ]; then make test_crash; fi
if [ -f test_edit.vim ]; then make test_edit; fi
if [ -f test_help.vim ]; then make test_help; fi
if [ -f test_ins_complete.vim ]; then make test_ins_complete; fi
if [ -f test_popup.vim ]; then make test_popup; fi
if [ -f test_startup.vim ]; then make test_startup; fi
if [ -f test_tagjump.vim ]; then make test_tagjump; fi
if [ -f test_visual.vim ]; then make test_visual; fi
if [ -f test_xxd.vim ]; then make test_xxd; fi
if [ -f test_tuple.vim ]; then make test_tuple; fi