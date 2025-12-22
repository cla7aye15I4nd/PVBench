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

typedef struct src_t {
     uint32_t a;
     float b;
  } src_t;

typedef struct dst_t {
     float b;
  } dst_t;

herr_t convert(hid_t src_id, hid_t dst_id, H5T_cdata_t *cdata,
    size_t nelmts, size_t buf_stride, size_t bkg_stride, void *buf,
    void *bkg, hid_t dxpl)
{
  herr_t retval = EXIT_SUCCESS;
  switch (cdata->command)
  {
  case H5T_CONV_INIT:
    printf("Initializing conversion function...\n");
    break;
  case H5T_CONV_CONV:
    printf("Converting...\n");
    for (size_t i = 0; i < nelmts; ++i)
      ((dst_t*) buf)[i].b = ((src_t*) buf)[i].b;
    break;
  case H5T_CONV_FREE:
    printf("Finalizing conversion function...\n");
    break;
  default:
    break;
  }
  return retval;
}

int main() {
  hid_t src = H5I_INVALID_HID;
  hid_t dst = H5I_INVALID_HID;
  hid_t file_id = H5I_INVALID_HID;
  hid_t space_id = H5I_INVALID_HID;
  hid_t dset_id = H5I_INVALID_HID;
  
  if ((src = H5Tcreate(H5T_COMPOUND, sizeof(struct src_t))) < 0) {
    printf("src dtype creation failed\n");
  }

  if (H5Tinsert(src, "a", HOFFSET(struct src_t, a), H5T_NATIVE_UINT32) < 0) {
    printf("dtype insertion failed\n");
  }

  if (H5Tinsert(src, "b", HOFFSET(struct src_t, b), H5T_NATIVE_FLOAT) < 0) {
    printf("dtype insertion failed\n");
  }

  if ((dst = H5Tcreate(H5T_COMPOUND, sizeof(struct dst_t))) < 0) {
    printf("dst dtype creation failed\n");
  }

  if (H5Tinsert(dst, "b", HOFFSET(struct dst_t, b), H5T_IEEE_F32LE) < 0) {
    printf("dtype insertion failed\n");
  }

  if (H5Tregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert) < 0) {
    printf("conversion registration failed\n");
  }

  struct src_t buf[] = {{1, 1.0} , {2, 2.0}, {3, 3.0}, {4, 4.0} , {5, 5.0} };  
  
  if ((file_id = H5Fcreate("conversion_test.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT)) < 0) {
    printf("file creation failed\n");
  }

  if ((space_id = H5Screate_simple(1, (const hsize_t[]) {5}, NULL)) < 0) {
    printf("space creation failed\n");
  }

  if ((dset_id = H5Dcreate(file_id, "dset", dst, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT)) < 0) {
    printf("dset creation failed\n");
  }

  printf("Beginning dataset write\n");

  if (H5Dwrite(dset_id, src, space_id, H5S_ALL, H5P_DEFAULT, buf) < 0) {
    printf("write failed\n");
  }

  H5Tclose(dst);
  H5Tclose(src);
  H5Fclose(file_id);
  H5Sclose(space_id);
  H5Dclose(dset_id);
  return 0;
}
EOF

if [ ! -z "${CC:-}" ]; then
    $CC $CFLAGS -o poc poc.c -I$HDF5_REPO_PATH/install/include -L$HDF5_REPO_PATH/install/lib -lhdf5 -Wl,-rpath=$HDF5_REPO_PATH/install/lib
fi