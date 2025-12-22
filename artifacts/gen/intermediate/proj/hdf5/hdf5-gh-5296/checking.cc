#include "hdf5.h"
#include <assert.h>

static void test_h5s_bug3(void)
{
    hsize_t dims[1] = {10};
    hsize_t start[1];
    hsize_t count[1] = {1};

    hid_t space1 = H5Screate_simple(1, dims, NULL);
    assert(space1 != -1);

    hid_t space2 = H5Screate_simple(1, dims, NULL);
    assert(space2 != -1);

    start[0] = 0;
    assert(H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL) != -1);

    start[0] = 1;
    assert(H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL) != -1);

    hid_t space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);
    assert(space3 != -1);

    assert(H5Sclose(space1) != -1);
    assert(H5Sclose(space2) != -1);
    assert(H5Sclose(space3) != -1);
}

int main(void)
{
    test_h5s_bug3();
    return 0;
}
