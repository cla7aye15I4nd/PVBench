#!/bin/bash -eu
USE_TRACKED_ALLOC=1 USE_ZEND_ALLOC=0 sapi/cli/php -f $1
