#include "hdf5.h"
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <stdint.h>

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
    assert(cdata != NULL);
    switch (cdata->command) {
    case H5T_CONV_CONV:
        assert(buf != NULL);
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
    htri_t tri;

    hid_t src = H5Tcreate(H5T_COMPOUND, sizeof(struct src_t));
    assert(src >= 0);
    ret = H5Tinsert(src, "a", HOFFSET(struct src_t, a), H5T_NATIVE_UINT32);
    assert(ret >= 0);
    ret = H5Tinsert(src, "b", HOFFSET(struct src_t, b), H5T_NATIVE_FLOAT);
    assert(ret >= 0);
    /* Semantic checks on source type */
    size_t sz = H5Tget_size(src);
    assert(sz == sizeof(struct src_t));
    int nmem = H5Tget_nmembers(src);
    assert(nmem == 2);
    hid_t memb_t = H5Tget_member_type(src, 1);
    assert(memb_t >= 0);
    tri = H5Tequal(memb_t, H5T_NATIVE_FLOAT);
    assert(tri > 0);
    ret = H5Tclose(memb_t);
    assert(ret >= 0);

    hid_t dst = H5Tcreate(H5T_COMPOUND, sizeof(struct dst_t));
    assert(dst >= 0);
    ret = H5Tinsert(dst, "b", HOFFSET(struct dst_t, b), H5T_IEEE_F32LE);
    assert(ret >= 0);
    /* Semantic checks on destination type */
    sz = H5Tget_size(dst);
    assert(sz == sizeof(struct dst_t));
    nmem = H5Tget_nmembers(dst);
    assert(nmem == 1);
    memb_t = H5Tget_member_type(dst, 0);
    assert(memb_t >= 0);
    tri = H5Tequal(memb_t, H5T_IEEE_F32LE);
    assert(tri > 0);
    ret = H5Tclose(memb_t);
    assert(ret >= 0);

    ret = H5Tregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert);
    assert(ret >= 0);

    struct src_t buf[] = {{1, 1.0f}, {2, 2.0f}, {3, 3.0f}, {4, 4.0f}, {5, 5.0f}};

    hid_t file_id = H5Fcreate("conversion_test.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file_id >= 0);

    hsize_t dims[1] = {5};
    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);
    /* Semantic checks on dataspace */
    int nd = H5Sget_simple_extent_ndims(space_id);
    assert(nd == 1);
    hsize_t got_dims[1];
    hsize_t max_dims[1];
    int nd2 = H5Sget_simple_extent_dims(space_id, got_dims, max_dims);
    assert(nd2 == 1);
    assert(got_dims[0] == 5);

    hid_t dset_id = H5Dcreate(file_id, "dset", dst, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);

    ret = H5Dwrite(dset_id, src, space_id, H5S_ALL, H5P_DEFAULT, buf);
    assert(ret >= 0);

    /* Semantic check: dataset type equals destination type */
    hid_t dset_type = H5Dget_type(dset_id);
    assert(dset_type >= 0);
    tri = H5Tequal(dset_type, dst);
    assert(tri > 0);
    ret = H5Tclose(dset_type);
    assert(ret >= 0);

    /* Read back and verify conversion results */
    dst_t out[5];
    ret = H5Dread(dset_id, dst, H5S_ALL, H5S_ALL, H5P_DEFAULT, out);
    assert(ret >= 0);
    for (size_t i = 0; i < 5; ++i) {
        assert(fabsf(out[i].b - buf[i].b) < 1e-6f);
    }

    /* Close resources - ensure closes succeed */
    ret = H5Tclose(dst);
    assert(ret >= 0);
    ret = H5Tclose(src);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);
    ret = H5Sclose(space_id);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);

    return 0;
}