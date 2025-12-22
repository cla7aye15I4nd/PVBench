#!/bin/bash -eu
echo "a" "?b:a"{1..10000} | build/bin/hermesc -dump-ast -
echo "a" "?b"{1..10000} | build/bin/hermesc -dump-ast -
