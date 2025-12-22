#!/bin/bash -eu
./buildconf
./configure
make -j$(nproc)

## The following tests are skipped because they are not stable
rm ext/standard/tests/file/file_get_contents_file_put_contents_5gb.phpt || true
rm ext/standard/tests/file/disk_free_space_basic.phpt || true

script -e -c "sapi/cli/php run-tests.php -q \
    -d opcache.jit=disable \
    -d opcache.protect_memory=1 \
    -d opcache.jit_buffer_size=64M \
    -j16 \
    -g FAIL,BORK,LEAK,XLEAK \
    --no-progress \
    --offline \
    --show-diff \
    --show-slow 1000 \
    --set-timeout 600"
