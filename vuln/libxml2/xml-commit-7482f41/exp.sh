#!/bin/bash
echo '<root/>' | ./xmllint --xpath `cat $1` -