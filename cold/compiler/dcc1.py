#!/usr/bin/env python3

import os
import subprocess
import sys


def check_and_append(argv, flag):
    if flag not in argv:
        argv.append(flag)


def build(llvmcc):
    argv = sys.argv[1:]

    argv = list(filter(lambda x: not x.startswith("-O") and not x.startswith("-g"), argv))

    check_and_append(argv, "-g")
    check_and_append(argv, "-O0")
    check_and_append(argv, "-Wno-everything")

    subprocess.check_call([llvmcc] + argv, env=os.environ)
