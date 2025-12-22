#!/bin/bash -eu
./build/bin/opt -passes=slp-vectorizer -slp-threshold=-99999 $1