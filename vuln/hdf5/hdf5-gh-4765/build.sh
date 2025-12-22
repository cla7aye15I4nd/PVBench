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

cat <<EOF > poc.cpp
#include "hdf5.h"
#include <stdio.h>
#include <stdlib.h>
#include <iostream>

#define FILE            "temp2.h5"
#define GROUPNAME       "./Data"
#define LINKNAME        "Data_link"


int main (void)
{
    hid_t           file, grpid, space, dset, dcpl;    /* Handles */
    herr_t          status;
					
	/*
     * Create a new file using the default properties.
     */
    file = H5Fcreate (FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
	
	grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
	
	std::cout << "Before H5Gmove" <<std::endl;
	status = H5Gmove2 (0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
	std::cout << "After H5Gmove" <<std::endl;
    	
	/*
     * Close and release resources.
     */
    status = H5Gclose(grpid);
    status = H5Fclose (file);

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    $CXX $CXXFLAGS -o poc poc.cpp -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi