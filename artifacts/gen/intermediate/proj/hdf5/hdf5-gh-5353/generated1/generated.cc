#include "hdf5.h"
#include <assert.h>

static void test_h5s_bug5(void)
{
    hsize_t dims[] = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];

    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);

    // Semantic: newly created simple dataspace should be of SIMPLE class
    H5S_class_t cls = H5Sget_simple_extent_type(space_id);
    assert(cls == H5S_SIMPLE);

    herr_t ret = H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);

    ret = H5Sset_extent_none(space_id);
    assert(ret >= 0);

    // Semantic: after setting extent none, the dataspace should be NULL class
    cls = H5Sget_simple_extent_type(space_id);
    assert(cls == H5S_NULL);

    H5E_BEGIN_TRY {
        ret = H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    } H5E_END_TRY;
    // Expected failure per dump.txt: hyperslab selections are unsupported for null extents
    assert(ret == -1);

    ret = H5Sclose(space_id);
    assert(ret >= 0);
}

int main(void)
{
    test_h5s_bug5();
    return 0;
}