#!/bin/bash -eu
./build/bin/clang-format $1 --style="{IndentPPDirectives: BeforeHash}"