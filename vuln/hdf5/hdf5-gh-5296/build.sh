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
test_h5s_bug3(void)
{
    hsize_t dims[1]  = {10};
    hsize_t start[1] = {0};
    hsize_t count[1] = {1};
    herr_t  ret      = 0;
    hid_t   space1   = H5I_INVALID_HID;
    hid_t   space2   = H5I_INVALID_HID;
    hid_t   space3   = H5I_INVALID_HID;

    space1 = H5Screate_simple(1, dims, NULL);
    space2 = H5Screate_simple(1, dims, NULL);
    /* Select a single, different element in each dataspace */
    start[0] = 0;
    count[0] = 1;
    ret      = H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL);

    start[0] = 1;
    count[0] = 1;
    ret      = H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL);

    /* Combine the selections with AND, resulting in a "none" selection.
     * H5Scombine_select previously used to attempt to set information
     * in a hyperslab-specific field, even when the resulting selection
     * wasn't a hyperslab.
     */
    space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);

    /* Close dataspaces */
    ret = H5Sclose(space1);
    ret = H5Sclose(space2);
    ret = H5Sclose(space3);
} /* test_h5s_bug3() */

int main(void) {
    test_h5s_bug3();
    return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi