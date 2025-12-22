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
#include <stdio.h>
#include <stdlib.h>

#define FILE_NAME "tid.h5"
#define DSET_NAME "Dataset 1"

static int
test_appropriate_ids(void)
{
    hid_t    file_id  = H5I_INVALID_HID;
    hid_t    fapl_id  = H5I_INVALID_HID;
    hid_t    fcpl_id  = H5I_INVALID_HID;
    hid_t    plist    = H5I_INVALID_HID;
    hid_t    dset_id  = H5I_INVALID_HID;
    hid_t    space_id = H5I_INVALID_HID;
    hsize_t  dims     = 2;
    hssize_t free_space;
    herr_t   ret = 0; /* Generic return value */

    fcpl_id = H5Pcreate(H5P_FILE_CREATE);
    file_id = H5Fcreate(FILE_NAME, H5F_ACC_TRUNC, fcpl_id, H5P_DEFAULT);

    space_id = H5Screate_simple(1, &dims, NULL);
    dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);

    ret = H5Pclose(fcpl_id);
    ret = H5Sclose(space_id);
    ret = H5Dclose(dset_id);
    ret = H5Fclose(file_id);

    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    fcpl_id = H5Fget_create_plist(file_id);
    fapl_id = H5Fget_access_plist(file_id);
    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);

    H5E_BEGIN_TRY
    {
        plist = H5Fget_create_plist(dset_id); /* dset_id is not file ID */
    }
    H5E_END_TRY
    H5E_BEGIN_TRY
    {
        plist = H5Fget_access_plist(fapl_id); /* fapl_id is not file ID */
    }
    H5E_END_TRY
    H5E_BEGIN_TRY
    {
        unsigned intent;                       /* File access flags */
        ret = H5Fget_intent(dset_id, &intent); /* dset_id is not file ID */
    }
    H5E_END_TRY
    H5E_BEGIN_TRY
    {
        unsigned long fileno = 0;
        ret                  = H5Fget_fileno(dset_id, &fileno); /* dset_id is not file ID */
    }
    H5E_END_TRY
    H5E_BEGIN_TRY
    {
        free_space = H5Fget_freespace(dset_id); /* dset_id is not file ID */
    }
    H5E_END_TRY
    H5E_BEGIN_TRY
    {
        void *os_file_handle = NULL;                                    /* OS file handle */
        ret = H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle); /* fapl_id is not file ID */
    }
    H5E_END_TRY

    ret = H5Pclose(fapl_id);
    ret = H5Pclose(fcpl_id);
    ret = H5Dclose(dset_id);
    ret = H5Fclose(file_id);

    return 0;
}
int main(void)
{
    test_appropriate_ids();
    return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi