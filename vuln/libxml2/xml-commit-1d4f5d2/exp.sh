#!/bin/bash
echo "<e/>" > test.xml
./xmllint --schema $1 test.xml --noout
