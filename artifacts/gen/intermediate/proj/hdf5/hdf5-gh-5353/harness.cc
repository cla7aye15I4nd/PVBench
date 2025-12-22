#include "hdf5.h"

static void test_h5s_bug5(void)
{
    hsize_t dims[] = {10};
    hsize_t start[] = {0};
    hsize_t count[] = {1};
    hsize_t blocks[1];
    hid_t space_id = H5Screate_simple(1, dims, NULL);
    H5Sselect_hyperslab(space_id, H5S_SELECT_SET, start, NULL, count, NULL);
    H5Sset_extent_none(space_id);
    H5E_BEGIN_TRY {
        H5Sget_select_hyper_blocklist(space_id, 0, 1, blocks);
    } H5E_END_TRY
    H5Sclose(space_id);
}

int main(void)
{
    test_h5s_bug5();
    return 0;
}