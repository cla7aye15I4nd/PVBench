#include "hdf5.h"
#include <assert.h>

#define FILE_NAME "tid.h5"
#define DSET_NAME "Dataset 1"

static int test_appropriate_ids(void)
{
    hsize_t dims = 2;

    // Create property list for file creation
    hid_t fcpl_id = H5Pcreate(H5P_FILE_CREATE);
    assert(fcpl_id >= 0);

    // Create file
    hid_t file_id = H5Fcreate(FILE_NAME, H5F_ACC_TRUNC, fcpl_id, H5P_DEFAULT);
    assert(file_id >= 0);

    // Create dataspace
    hid_t space_id = H5Screate_simple(1, &dims, NULL);
    assert(space_id >= 0);

    // Semantic checks on dataspace
    int ndims = H5Sget_simple_extent_ndims(space_id);
    assert(ndims == 1);
    hsize_t cur_dims[1] = {0};
    int got_ndims = H5Sget_simple_extent_dims(space_id, cur_dims, NULL);
    assert(got_ndims == 1);
    assert(cur_dims[0] == dims);

    // Create dataset
    hid_t dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);

    // Semantic: verify dataset space matches expected
    hid_t dset_space = H5Dget_space(dset_id);
    assert(dset_space >= 0);
    int dset_ndims = H5Sget_simple_extent_ndims(dset_space);
    assert(dset_ndims == 1);
    hsize_t dset_dims[1] = {0};
    int dset_dims_ndims = H5Sget_simple_extent_dims(dset_space, dset_dims, NULL);
    assert(dset_dims_ndims == 1);
    assert(dset_dims[0] == dims);
    herr_t ret = H5Sclose(dset_space);
    assert(ret >= 0);

    // Close initial handles
    ret = H5Pclose(fcpl_id);
    assert(ret >= 0);
    ret = H5Sclose(space_id);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);

    // Reopen file and objects for further testing
    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    assert(file_id >= 0);

    fcpl_id = H5Fget_create_plist(file_id);
    assert(fcpl_id >= 0);

    hid_t fapl_id = H5Fget_access_plist(file_id);
    assert(fapl_id >= 0);

    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);
    assert(dset_id >= 0);

    // Semantic: confirm the file is opened read-only
    unsigned good_intent = 0;
    ret = H5Fget_intent(file_id, &good_intent);
    assert(ret >= 0);
    assert((good_intent & H5F_ACC_RDWR) == 0); // should not have write intent

    // Negative tests expected to fail (using inappropriate IDs)

    // H5Fget_create_plist with dataset ID should fail
    hid_t bad_plist1 = -1;
    H5E_BEGIN_TRY {
        bad_plist1 = H5Fget_create_plist(dset_id);
    } H5E_END_TRY
    assert(bad_plist1 < 0);

    // H5Fget_access_plist with fapl_id (not a file ID) should fail
    hid_t bad_plist2 = -1;
    H5E_BEGIN_TRY {
        bad_plist2 = H5Fget_access_plist(fapl_id);
    } H5E_END_TRY
    assert(bad_plist2 < 0);

    // H5Fget_intent with dataset ID should fail
    unsigned intent = 0;
    ret = 0;
    H5E_BEGIN_TRY {
        ret = H5Fget_intent(dset_id, &intent);
    } H5E_END_TRY
    assert(ret < 0);

    // H5Fget_fileno with dataset ID should fail
    unsigned long fileno = 0;
    ret = 0;
    H5E_BEGIN_TRY {
        ret = H5Fget_fileno(dset_id, &fileno);
    } H5E_END_TRY
    assert(ret < 0);

    // H5Fget_freespace with dataset ID should fail
    hssize_t free_space = 0;
    H5E_BEGIN_TRY {
        free_space = H5Fget_freespace(dset_id);
    } H5E_END_TRY
    assert(free_space < 0);

    // H5Fget_vfd_handle with fapl_id (not a file ID) should fail
    void *os_file_handle = NULL;
    ret = 0;
    H5E_BEGIN_TRY {
        ret = H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle);
    } H5E_END_TRY
    assert(ret < 0);
    // On failure, the output handle should remain NULL
    assert(os_file_handle == NULL);

    // Close resources
    ret = H5Pclose(fapl_id);
    assert(ret >= 0);
    ret = H5Pclose(fcpl_id);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);

    return 0;
}

int main(void)
{
    test_appropriate_ids();
    return 0;
}
