#!/bin/bash
echo "<Child xmlns="http://www.test.com">5</Child>" > test.xml
./xmllint --schema $1 test.xml --noout
