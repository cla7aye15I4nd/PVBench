#include "hdf5.h"
#include <cassert>

static void test_h5s_bug3(void)
{
    hsize_t dims[1] = {10};
    hsize_t start[1];
    hsize_t count[1] = {1};

    hid_t space1 = H5Screate_simple(1, dims, NULL);
    assert(space1 >= 0);
    hid_t space2 = H5Screate_simple(1, dims, NULL);
    assert(space2 >= 0);

    // Semantic check: extents are correct
    hssize_t total_points1 = H5Sget_simple_extent_npoints(space1);
    assert(total_points1 == 10);
    hssize_t total_points2 = H5Sget_simple_extent_npoints(space2);
    assert(total_points2 == 10);

    start[0] = 0;
    herr_t ret = H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);
    // After selecting a single element, selection count should be 1
    hssize_t sel_points1 = H5Sget_select_npoints(space1);
    assert(sel_points1 == 1);

    start[0] = 1;
    ret = H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);
    hssize_t sel_points2 = H5Sget_select_npoints(space2);
    assert(sel_points2 == 1);

    hid_t space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);
    assert(space3 >= 0);

    // Intersection of two disjoint singletons should be empty
    hssize_t combined_sel_points = H5Sget_select_npoints(space3);
    assert(combined_sel_points == 0);

    // Extents should be preserved in the combined dataspace
    hssize_t total_points3 = H5Sget_simple_extent_npoints(space3);
    assert(total_points3 == 10);

    ret = H5Sclose(space1);
    assert(ret >= 0);
    ret = H5Sclose(space2);
    assert(ret >= 0);
    ret = H5Sclose(space3);
    assert(ret >= 0);
}

int main(void)
{
    test_h5s_bug3();
    return 0;
}
