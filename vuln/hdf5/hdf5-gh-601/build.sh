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
#include <stdlib.h>
#define LOG_LOCATION "cache_logging.out"

int main() {
   hid_t   fapl = -1;
    hbool_t is_enabled;
    hbool_t is_enabled_out;
    hbool_t start_on_access;
    hbool_t start_on_access_out;
    char *  location = NULL;
    size_t  size;

    hid_t   fid = -1;
    hid_t   gid = -1;
    hbool_t is_currently_logging;
    char    group_name[12];
    char    filename[1024];
    int     i;

    fapl = H5Pcreate(H5P_FILE_ACCESS);
    H5Pset_fapl_core(fapl, 0, 0);

    /* Set up metadata cache logging */
    is_enabled      = 1;
    start_on_access = 0;
    H5Pset_mdc_log_options(fapl, is_enabled, LOG_LOCATION, start_on_access);
    H5Pset_mdc_log_options(fapl, is_enabled, LOG_LOCATION, start_on_access);

    H5Fclose(fapl);

  return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi