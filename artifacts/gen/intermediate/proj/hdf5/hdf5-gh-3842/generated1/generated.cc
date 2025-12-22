#include "hdf5.h"
#include <stdlib.h>
#include <cassert>
#include <cstdint>
#include <cmath>
#include <cstring>

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
    switch (cdata->command) {
    case H5T_CONV_CONV:
        for (size_t i = 0; i < nelmts; ++i)
            ((dst_t*)buf)[i].b = ((src_t*)buf)[i].b;
        break;
    default:
        break;
    }
    return EXIT_SUCCESS;
}

int main()
{
    herr_t ret;

    hid_t src = H5Tcreate(H5T_COMPOUND, sizeof(struct src_t));
    assert(src >= 0);
    ret = H5Tinsert(src, "a", HOFFSET(struct src_t, a), H5T_NATIVE_UINT32);
    assert(ret >= 0);
    ret = H5Tinsert(src, "b", HOFFSET(struct src_t, b), H5T_NATIVE_FLOAT);
    assert(ret >= 0);

    hid_t dst = H5Tcreate(H5T_COMPOUND, sizeof(struct dst_t));
    assert(dst >= 0);
    ret = H5Tinsert(dst, "b", HOFFSET(struct dst_t, b), H5T_IEEE_F32LE);
    assert(ret >= 0);

    // Semantic checks on datatypes
    size_t sz_src = H5Tget_size(src);
    assert(sz_src == sizeof(struct src_t));
    size_t sz_dst = H5Tget_size(dst);
    assert(sz_dst == sizeof(struct dst_t));

    int nmembers_src = H5Tget_nmembers(src);
    assert(nmembers_src == 2);
    int nmembers_dst = H5Tget_nmembers(dst);
    assert(nmembers_dst == 1);

    size_t off_src_a = H5Tget_member_offset(src, 0);
    assert(off_src_a == HOFFSET(struct src_t, a));
    size_t off_src_b = H5Tget_member_offset(src, 1);
    assert(off_src_b == HOFFSET(struct src_t, b));
    size_t off_dst_b = H5Tget_member_offset(dst, 0);
    assert(off_dst_b == HOFFSET(struct dst_t, b));

    char* name_src0 = H5Tget_member_name(src, 0);
    assert(name_src0 != NULL && std::strcmp(name_src0, "a") == 0);
    H5free_memory(name_src0);
    char* name_src1 = H5Tget_member_name(src, 1);
    assert(name_src1 != NULL && std::strcmp(name_src1, "b") == 0);
    H5free_memory(name_src1);
    char* name_dst0 = H5Tget_member_name(dst, 0);
    assert(name_dst0 != NULL && std::strcmp(name_dst0, "b") == 0);
    H5free_memory(name_dst0);

    ret = H5Tregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert);
    assert(ret >= 0);

    struct src_t buf[] = {{1, 1.0f}, {2, 2.0f}, {3, 3.0f}, {4, 4.0f}, {5, 5.0f}};

    hid_t file_id = H5Fcreate("conversion_test.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file_id >= 0);

    hsize_t dims[1] = {5};
    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);

    // Semantic checks on dataspace
    int ndims = H5Sget_simple_extent_ndims(space_id);
    assert(ndims == 1);
    hsize_t check_dims[1] = {0};
    H5Sget_simple_extent_dims(space_id, check_dims, NULL);
    assert(check_dims[0] == 5);

    hid_t dset_id = H5Dcreate(file_id, "dset", dst, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);

    ret = H5Dwrite(dset_id, src, space_id, H5S_ALL, H5P_DEFAULT, buf);
    assert(ret >= 0);

    // Read back and verify conversion semantics
    dst_t outbuf[5];
    ret = H5Dread(dset_id, dst, space_id, H5S_ALL, H5P_DEFAULT, outbuf);
    assert(ret >= 0);
    for (size_t i = 0; i < 5; ++i) {
        assert(std::fabs(outbuf[i].b - buf[i].b) < 1e-6f);
    }

    ret = H5Tclose(dst);
    assert(ret >= 0);
    ret = H5Tclose(src);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);
    ret = H5Sclose(space_id);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);

    return 0;
}