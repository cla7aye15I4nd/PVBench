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

    // Create simple dataspace
    hid_t space_id = H5Screate_simple(1, &dims, NULL);
    assert(space_id >= 0);
    // Semantic checks on dataspace
    int ndims = H5Sget_simple_extent_ndims(space_id);
    assert(ndims == 1);
    hssize_t npoints = H5Sget_simple_extent_npoints(space_id);
    assert(npoints == (hssize_t)dims);

    // Create dataset
    hid_t dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);

    // Close creation resources
    herr_t ret;
    ret = H5Pclose(fcpl_id);
    assert(ret >= 0);
    ret = H5Sclose(space_id);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);

    // Reopen file read-only and query properties
    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    assert(file_id >= 0);

    fcpl_id = H5Fget_create_plist(file_id);
    assert(fcpl_id >= 0);

    hid_t fapl_id = H5Fget_access_plist(file_id);
    assert(fapl_id >= 0);

    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);
    assert(dset_id >= 0);

    // Semantic check: file was opened read-only, so intent must not include RDWR
    unsigned intent_ok = 0;
    ret = H5Fget_intent(file_id, &intent_ok);
    assert(ret >= 0);
    assert((intent_ok & H5F_ACC_RDWR) == 0);

    // Expected failures with inappropriate IDs
    hid_t plist_bad1; // expected: -1
    H5E_BEGIN_TRY {
        plist_bad1 = H5Fget_create_plist(dset_id);
    } H5E_END_TRY;
    assert(plist_bad1 < 0);

    hid_t plist_bad2; // expected: -1
    H5E_BEGIN_TRY {
        plist_bad2 = H5Fget_access_plist(fapl_id);
    } H5E_END_TRY;
    assert(plist_bad2 < 0);

    herr_t ret_bad1; // expected: -1
    H5E_BEGIN_TRY {
        unsigned intent;
        ret_bad1 = H5Fget_intent(dset_id, &intent);
    } H5E_END_TRY;
    assert(ret_bad1 < 0);

    herr_t ret_bad2; // expected: -1
    H5E_BEGIN_TRY {
        unsigned long fileno = 0;
        ret_bad2 = H5Fget_fileno(dset_id, &fileno);
    } H5E_END_TRY;
    assert(ret_bad2 < 0);

    hssize_t free_space_bad; // expected: -1
    H5E_BEGIN_TRY {
        free_space_bad = H5Fget_freespace(dset_id);
    } H5E_END_TRY;
    assert(free_space_bad < 0);

    herr_t ret_bad3; // expected: -1
    H5E_BEGIN_TRY {
        void *os_file_handle = NULL;
        ret_bad3 = H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle);
    } H5E_END_TRY;
    assert(ret_bad3 < 0);

    // Close remaining resources
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
