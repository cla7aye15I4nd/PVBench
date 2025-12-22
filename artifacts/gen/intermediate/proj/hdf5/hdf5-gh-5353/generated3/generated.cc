#include "hdf5.h"
#include <cassert>

static void test_h5s_bug5(void)
{
    hsize_t dims[] = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];

    // Semantic pre-checks on selection parameters
    assert(dims[0] > 0);
    assert(start[0] < dims[0]);
    assert(count[0] >= 1);
    assert(count[0] <= (dims[0] - start[0]));

    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);

    herr_t ret = H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);

    ret = H5Sset_extent_none(space_id);
    assert(ret >= 0);

    herr_t ret_fail;
    H5E_BEGIN_TRY {
        ret_fail = H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    } H5E_END_TRY
    assert(ret_fail < 0); // Expected failure: hyperslab selections unsupported for null extents

    ret = H5Sclose(space_id);
    assert(ret >= 0);
}

int main(void)
{
    test_h5s_bug5();
    return 0;
}