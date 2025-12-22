#include "hdf5.h"
#include <assert.h>

static void test_h5s_bug5(void)
{
    hsize_t dims[] = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];
    herr_t ret;

    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id != -1);

    assert(H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL) != -1);
    assert(H5Sset_extent_none(space_id) != -1);

    // This should fail - hyperslab selections are unsupported for null extents
    H5E_BEGIN_TRY {
        ret = H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    } H5E_END_TRY
    assert(ret == -1);

    assert(H5Sclose(space_id) != -1);
}

int main(void)
{
    test_h5s_bug5();
    return 0;
}
