#include "hdf5.h"

static void test_h5s_bug3(void)
{
    hsize_t dims[1] = {10};
    hsize_t start[1];
    hsize_t count[1] = {1};
    hid_t space1 = H5Screate_simple(1, dims, NULL);
    hid_t space2 = H5Screate_simple(1, dims, NULL);

    start[0] = 0;
    H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL);

    start[0] = 1;
    H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL);

    hid_t space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);

    H5Sclose(space1);
    H5Sclose(space2);
    H5Sclose(space3);
}

int main(void)
{
    test_h5s_bug3();
    return 0;
}