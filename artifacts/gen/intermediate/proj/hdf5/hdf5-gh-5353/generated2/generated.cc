#include "hdf5.h"
#include <assert.h>

static void test_h5s_bug5(void)
{
    hsize_t dims[] = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];

    // Create a simple 1-D dataspace of size 10
    hid_t space_id = H5Screate_simple(1, dims, NULL);
    assert(space_id >= 0);

    // Select a hyperslab on the simple dataspace
    herr_t ret = H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);

    // Set the dataspace extent to none (NULL dataspace)
    ret = H5Sset_extent_none(space_id);
    assert(ret >= 0);

    // Semantic check: After setting extent none, the dataspace type must be H5S_NULL
    H5S_class_t cls = H5Sget_simple_extent_type(space_id);
    assert(cls == H5S_NULL);

    // Attempt to get hyperslab blocklist on a NULL-extent dataspace; expect failure
    H5E_BEGIN_TRY {
        ret = H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    } H5E_END_TRY
    assert(ret == -1);  // Expected failure per dump.txt

    // Close the dataspace
    herr_t ret_close = H5Sclose(space_id);
    assert(ret_close >= 0);
}

int main(void)
{
    test_h5s_bug5();
    return 0;
}
