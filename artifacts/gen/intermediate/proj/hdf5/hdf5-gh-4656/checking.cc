#include "hdf5.h"
#include <assert.h>

#define FILE_NAME "tid.h5"
#define DSET_NAME "Dataset 1"

static int test_appropriate_ids(void)
{
    hsize_t dims = 2;
    hid_t plist;
    hssize_t free_space;

    hid_t fcpl_id = H5Pcreate(H5P_FILE_CREATE);
    assert(fcpl_id != -1);

    hid_t file_id = H5Fcreate(FILE_NAME, H5F_ACC_TRUNC, fcpl_id, H5P_DEFAULT);
    assert(file_id != -1);

    hid_t space_id = H5Screate_simple(1, &dims, NULL);
    assert(space_id != -1);

    hid_t dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id != -1);

    assert(H5Pclose(fcpl_id) != -1);
    assert(H5Sclose(space_id) != -1);
    assert(H5Dclose(dset_id) != -1);
    assert(H5Fclose(file_id) != -1);

    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    assert(file_id != -1);

    fcpl_id = H5Fget_create_plist(file_id);
    assert(fcpl_id != -1);

    hid_t fapl_id = H5Fget_access_plist(file_id);
    assert(fapl_id != -1);

    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);
    assert(dset_id != -1);

    // Test with wrong IDs - these should fail
    H5E_BEGIN_TRY {
        plist = H5Fget_create_plist(dset_id);  // dset_id is not file ID
    } H5E_END_TRY
    assert(plist == -1);

    H5E_BEGIN_TRY {
        plist = H5Fget_access_plist(fapl_id);  // fapl_id is not file ID
    } H5E_END_TRY
    assert(plist == -1);

    H5E_BEGIN_TRY {
        unsigned intent;
        herr_t ret = H5Fget_intent(dset_id, &intent);  // dset_id is not file ID
        assert(ret == -1);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        unsigned long fileno = 0;
        herr_t ret = H5Fget_fileno(dset_id, &fileno);  // dset_id is not file ID
        assert(ret == -1);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        free_space = H5Fget_freespace(dset_id);  // dset_id is not file ID
        assert(free_space == -1);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        void *os_file_handle = NULL;
        herr_t ret = H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle);  // fapl_id is not file ID
        assert(ret == -1);
    } H5E_END_TRY

    assert(H5Pclose(fapl_id) != -1);
    assert(H5Pclose(fcpl_id) != -1);
    assert(H5Dclose(dset_id) != -1);
    assert(H5Fclose(file_id) != -1);

    return 0;
}

int main(void)
{
    return test_appropriate_ids();
}
