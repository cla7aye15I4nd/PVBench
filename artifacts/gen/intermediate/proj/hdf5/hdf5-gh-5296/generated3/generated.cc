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

    // Basic extent sanity checks
    int rank = H5Sget_simple_extent_ndims(space1);
    assert(rank == 1);
    hssize_t total_pts = H5Sget_simple_extent_npoints(space1);
    assert(total_pts == 10);

    // Verify selection parameters are within bounds
    assert(count[0] >= 1 && count[0] <= dims[0]);

    start[0] = 0;
    assert(start[0] < dims[0]);
    herr_t ret = H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);

    // After selection, expect exactly 1 selected element
    hssize_t sel_pts1 = H5Sget_select_npoints(space1);
    assert(sel_pts1 == 1);

    start[0] = 1;
    assert(start[0] < dims[0]);
    ret = H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);

    hssize_t sel_pts2 = H5Sget_select_npoints(space2);
    assert(sel_pts2 == 1);

    hid_t space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);
    assert(space3 >= 0);

    // Combined dataspace should have the same extent
    rank = H5Sget_simple_extent_ndims(space3);
    assert(rank == 1);
    total_pts = H5Sget_simple_extent_npoints(space3);
    assert(total_pts == 10);

    // Intersection of disjoint single-element selections should be empty
    hssize_t sel_pts3 = H5Sget_select_npoints(space3);
    assert(sel_pts3 == 0);

    // Inputs should remain unchanged by combine
    sel_pts1 = H5Sget_select_npoints(space1);
    assert(sel_pts1 == 1);
    sel_pts2 = H5Sget_select_npoints(space2);
    assert(sel_pts2 == 1);

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
