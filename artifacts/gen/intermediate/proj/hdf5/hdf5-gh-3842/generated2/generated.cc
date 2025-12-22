#include "hdf5.h"
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <string.h>

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
    (void)src_id; (void)dst_id; (void)buf_stride; (void)bkg_stride; (void)bkg; (void)dxpl;
    assert(cdata != NULL);
    switch (cdata->command) {
    case H5T_CONV_CONV:
        for (size_t i = 0; i < nelmts; ++i)
            ((dst_t*)buf)[i].b = ((src_t*)buf)[i].b;
        break;
    default:
        break;
    }
    return EXIT_SUCCESS; // >= 0 indicates success
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

    // Semantic checks for src compound type
    size_t src_size = H5Tget_size(src);
    assert(src_size == sizeof(struct src_t));
    int src_nmem = H5Tget_nmembers(src);
    assert(src_nmem == 2);
    char *src_m0 = H5Tget_member_name(src, 0);
    assert(src_m0 != NULL && strcmp(src_m0, "a") == 0);
    assert(H5Tget_member_offset(src, 0) == HOFFSET(struct src_t, a));
    hid_t src_m0_t = H5Tget_member_type(src, 0);
    assert(src_m0_t >= 0);
    assert(H5Tequal(src_m0_t, H5T_NATIVE_UINT32) > 0);
    assert(H5Tclose(src_m0_t) >= 0);
    assert(H5free_memory(src_m0) >= 0);

    char *src_m1 = H5Tget_member_name(src, 1);
    assert(src_m1 != NULL && strcmp(src_m1, "b") == 0);
    assert(H5Tget_member_offset(src, 1) == HOFFSET(struct src_t, b));
    hid_t src_m1_t = H5Tget_member_type(src, 1);
    assert(src_m1_t >= 0);
    assert(H5Tequal(src_m1_t, H5T_NATIVE_FLOAT) > 0);
    assert(H5Tclose(src_m1_t) >= 0);
    assert(H5free_memory(src_m1) >= 0);

    hid_t dst = H5Tcreate(H5T_COMPOUND, sizeof(struct dst_t));
    assert(dst >= 0);
    ret = H5Tinsert(dst, "b", HOFFSET(struct dst_t, b), H5T_IEEE_F32LE);
    assert(ret >= 0);

    // Semantic checks for dst compound type
    size_t dst_size = H5Tget_size(dst);
    assert(dst_size == sizeof(struct dst_t));
    int dst_nmem = H5Tget_nmembers(dst);
    assert(dst_nmem == 1);
    char *dst_m0 = H5Tget_member_name(dst, 0);
    assert(dst_m0 != NULL && strcmp(dst_m0, "b") == 0);
    assert(H5Tget_member_offset(dst, 0) == HOFFSET(struct dst_t, b));
    hid_t dst_m0_t = H5Tget_member_type(dst, 0);
    assert(dst_m0_t >= 0);
    assert(H5Tequal(dst_m0_t, H5T_IEEE_F32LE) > 0);
    assert(H5Tclose(dst_m0_t) >= 0);
    assert(H5free_memory(dst_m0) >= 0);

    ret = H5Tregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert);
    assert(ret >= 0);

    struct src_t buf[] = {{1, 1.0f}, {2, 2.0f}, {3, 3.0f}, {4, 4.0f}, {5, 5.0f}};

    hsize_t dims[1] = {5};
    hid_t file_id = H5Fcreate("conversion_test.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file_id >= 0);
    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);

    // Verify dataspace properties
    int sdims = H5Sget_simple_extent_ndims(space_id);
    assert(sdims == 1);
    hsize_t curdims[1];
    hsize_t maxdims[1];
    int nd_ok = H5Sget_simple_extent_dims(space_id, curdims, maxdims);
    assert(nd_ok >= 0);
    assert(curdims[0] == dims[0]);

    hid_t dset_id = H5Dcreate(file_id, "dset", dst, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);

    ret = H5Dwrite(dset_id, src, space_id, H5S_ALL, H5P_DEFAULT, buf);
    assert(ret >= 0);

    // Verify dataset's datatype matches expected dst type
    hid_t dtype = H5Dget_type(dset_id);
    assert(dtype >= 0);
    assert(H5Tequal(dtype, dst) > 0);
    assert(H5Tclose(dtype) >= 0);

    // Verify dataset's dataspace dimensions
    hid_t dspace = H5Dget_space(dset_id);
    assert(dspace >= 0);
    int d_nd = H5Sget_simple_extent_ndims(dspace);
    assert(d_nd == 1);
    hsize_t d_dims[1];
    hsize_t d_maxdims[1];
    assert(H5Sget_simple_extent_dims(dspace, d_dims, d_maxdims) >= 0);
    assert(d_dims[0] == dims[0]);
    assert(H5Sclose(dspace) >= 0);

    // Read back data and semantically validate conversion preserved 'b'
    struct dst_t out[5];
    ret = H5Dread(dset_id, dst, H5S_ALL, H5S_ALL, H5P_DEFAULT, out);
    assert(ret >= 0);
    for (size_t i = 0; i < 5; ++i) {
        assert(fabsf(out[i].b - buf[i].b) < 1e-6f);
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