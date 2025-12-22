#include "hdf5.h"
#include <assert.h>

static void test_h5s_bug3(void)
{
    hsize_t dims[1] = {10};
    hsize_t start[1];
    hsize_t count[1] = {1};

    hid_t space1 = H5Screate_simple(1, dims, NULL);
    assert(space1 >= 0);
    hid_t space2 = H5Screate_simple(1, dims, NULL);
    assert(space2 >= 0);

    // Basic semantic checks on created dataspaces
    int rank1 = H5Sget_simple_extent_ndims(space1);
    assert(rank1 == 1);
    int rank2 = H5Sget_simple_extent_ndims(space2);
    assert(rank2 == 1);

    hssize_t total_pts1 = H5Sget_simple_extent_npoints(space1);
    assert(total_pts1 == 10);
    hssize_t total_pts2 = H5Sget_simple_extent_npoints(space2);
    assert(total_pts2 == 10);

    hsize_t rdims1[1];
    hsize_t rdims2[1];
    assert(H5Sget_simple_extent_dims(space1, rdims1, NULL) >= 0);
    assert(H5Sget_simple_extent_dims(space2, rdims2, NULL) >= 0);
    assert(rdims1[0] == dims[0]);
    assert(rdims2[0] == dims[0]);

    // Select hyperslab at index 0 in space1
    start[0] = 0;
    assert(start[0] < dims[0]);
    herr_t ret = H5Sselect_hyperslab(space1, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);
    htri_t tri = H5Sselect_valid(space1);
    assert(tri > 0);
    hssize_t sel_pts1 = H5Sget_select_npoints(space1);
    assert(sel_pts1 == 1);

    // Select hyperslab at index 1 in space2
    start[0] = 1;
    assert(start[0] < dims[0]);
    ret = H5Sselect_hyperslab(space2, H5S_SELECT_SET, start, NULL, count, NULL);
    assert(ret >= 0);
    tri = H5Sselect_valid(space2);
    assert(tri > 0);
    hssize_t sel_pts2 = H5Sget_select_npoints(space2);
    assert(sel_pts2 == 1);

    // Combine selections using logical AND; expect empty selection
    hid_t space3 = H5Scombine_select(space1, H5S_SELECT_AND, space2);
    assert(space3 >= 0);

    int rank3 = H5Sget_simple_extent_ndims(space3);
    assert(rank3 == 1);
    hsize_t rdims3[1];
    assert(H5Sget_simple_extent_dims(space3, rdims3, NULL) >= 0);
    assert(rdims3[0] == dims[0]);

    htri_t tri3 = H5Sselect_valid(space3);
    assert(tri3 > 0);
    hssize_t sel_pts3 = H5Sget_select_npoints(space3);
    assert(sel_pts3 == 0); // Intersection of disjoint singletons should be empty

    // Close resources
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
