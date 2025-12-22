#!/bin/bash -eu
printf 'ev 1 + 3\nev 2 ** 3\nq\n' | sapi/phpdbg/phpdbg $1
