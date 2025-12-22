#include "hdf5.h"
#include <stdlib.h>
#include <assert.h>

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
    hid_t src = H5Tcreate(H5T_COMPOUND, sizeof(struct src_t));
    assert(src != -1);

    assert(H5Tinsert(src, "a", HOFFSET(struct src_t, a), H5T_NATIVE_UINT32) != -1);
    assert(H5Tinsert(src, "b", HOFFSET(struct src_t, b), H5T_NATIVE_FLOAT) != -1);

    hid_t dst = H5Tcreate(H5T_COMPOUND, sizeof(struct dst_t));
    assert(dst != -1);

    assert(H5Tinsert(dst, "b", HOFFSET(struct dst_t, b), H5T_IEEE_F32LE) != -1);

    assert(H5Tregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert) != -1);

    struct src_t buf[] = {{1, 1.0}, {2, 2.0}, {3, 3.0}, {4, 4.0}, {5, 5.0}};

    hid_t file_id = H5Fcreate("conversion_test.h5", H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file_id != -1);

    hid_t space_id = H5Screate_simple(1, (const hsize_t[]){5}, NULL);
    assert(space_id != -1);

    hid_t dset_id = H5Dcreate(file_id, "dset", dst, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id != -1);

    assert(H5Dwrite(dset_id, src, space_id, H5S_ALL, H5P_DEFAULT, buf) != -1);

    assert(H5Tunregister(H5T_PERS_SOFT, "src_t->dst_t", src, dst, &convert) != -1);
    assert(H5Tclose(dst) != -1);
    assert(H5Tclose(src) != -1);
    assert(H5Fclose(file_id) != -1);
    assert(H5Sclose(space_id) != -1);
    assert(H5Dclose(dset_id) != -1);

    return 0;
}
