#!/bin/bash -eu
printf 'b 6\nr\nw a $a\nc\nq\n' | sapi/phpdbg/phpdbg $1
