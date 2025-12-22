#!/bin/bash -eu
./src/vim -u NONE -X -Z -e -s -S $1 -c ':qa!'
