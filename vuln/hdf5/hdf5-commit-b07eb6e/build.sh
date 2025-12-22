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

int main(int argc, char **argv)
{
    if (argc != 2) {
        printf("Usage: %s <filename>\n", argv[0]);
        return -1;
    }

    const char *filename = argv[1];

    hid_t   fid = -1;   /* File ID */
    H5O_info_t oinfo;   /* Structure for object metadata information */
    herr_t  ret;        /* Generic return value */

    fid = H5Fopen(filename, H5F_ACC_RDONLY, H5P_DEFAULT);

    /* Case (1) */
    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/soft_two", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;

    /* Case (2) */
    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/dsetA", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;
    
    /* Case (3) */
    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/soft_one", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;
    
    /* Close the file */
    ret = H5Fclose(fid);

    return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi