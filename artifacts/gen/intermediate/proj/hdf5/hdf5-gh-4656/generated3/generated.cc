#include "hdf5.h"
#include <assert.h>

#define FILE_NAME "tid.h5"
#define DSET_NAME "Dataset 1"

static int test_appropriate_ids(void)
{
    herr_t ret;
    hsize_t dims = 2;

    /* Create objects */
    hid_t fcpl_id = H5Pcreate(H5P_FILE_CREATE);
    assert(fcpl_id >= 0);

    hid_t file_id = H5Fcreate(FILE_NAME, H5F_ACC_TRUNC, fcpl_id, H5P_DEFAULT);
    assert(file_id >= 0);

    hid_t space_id = H5Screate_simple(1, &dims, NULL);
    assert(space_id >= 0);
    /* Semantic checks on dataspace */
    {
        int ndims = H5Sget_simple_extent_ndims(space_id);
        assert(ndims == 1);
        hssize_t npoints = H5Sget_simple_extent_npoints(space_id);
        assert(npoints == (hssize_t)dims);
    }

    hid_t dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(dset_id >= 0);
    /* Semantic checks on dataset: space and type */
    {
        hid_t dspace2 = H5Dget_space(dset_id);
        assert(dspace2 >= 0);
        int nd2 = H5Sget_simple_extent_ndims(dspace2);
        assert(nd2 == 1);
        hssize_t np2 = H5Sget_simple_extent_npoints(dspace2);
        assert(np2 == (hssize_t)dims);
        ret = H5Sclose(dspace2);
        assert(ret >= 0);

        hid_t dtype = H5Dget_type(dset_id);
        assert(dtype >= 0);
        int teq = H5Tequal(dtype, H5T_NATIVE_INT);
        assert(teq > 0);
        ret = H5Tclose(dtype);
        assert(ret >= 0);
    }

    ret = H5Pclose(fcpl_id);
    assert(ret >= 0);
    ret = H5Sclose(space_id);
    assert(ret >= 0);
    ret = H5Dclose(dset_id);
    assert(ret >= 0);
    ret = H5Fclose(file_id);
    assert(ret >= 0);

    /* Reopen and query */
    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    assert(file_id >= 0);

    fcpl_id = H5Fget_create_plist(file_id);
    assert(fcpl_id >= 0);

    hid_t fapl_id = H5Fget_access_plist(file_id);
    assert(fapl_id >= 0);

    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);
    assert(dset_id >= 0);

    /* Semantic: on a read-only open, intent must not include RDWR */
    {
        unsigned intent = 0;
        ret = H5Fget_intent(file_id, &intent);
        assert(ret >= 0);
        assert((intent & H5F_ACC_RDWR) == 0);
    }

    /* Semantic: free space query on a valid file id should succeed */
    {
        hssize_t free_space_ok = H5Fget_freespace(file_id);
        assert(free_space_ok >= 0);
    }

    /* Expected failures with inappropriate IDs */
    hid_t bad_plist_from_dset = 0;
    H5E_BEGIN_TRY {
        bad_plist_from_dset = H5Fget_create_plist(dset_id);
    } H5E_END_TRY
    assert(bad_plist_from_dset == -1);

    hid_t bad_access_from_fapl = 0;
    H5E_BEGIN_TRY {
        bad_access_from_fapl = H5Fget_access_plist(fapl_id);
    } H5E_END_TRY
    assert(bad_access_from_fapl == -1);

    H5E_BEGIN_TRY {
        unsigned intent_bad = 0;
        ret = H5Fget_intent(dset_id, &intent_bad);
    } H5E_END_TRY
    assert(ret == -1);

    H5E_BEGIN_TRY {
        unsigned long fileno = 0;
        ret = H5Fget_fileno(dset_id, &fileno);
    } H5E_END_TRY
    assert(ret == -1);

    hssize_t free_space_bad = 0;
    H5E_BEGIN_TRY {
        free_space_bad = H5Fget_freespace(dset_id);
    } H5E_END_TRY
    assert(free_space_bad == -1);

    H5E_BEGIN_TRY {
        void *os_file_handle = NULL;
        ret = H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle);
    } H5E_END_TRY
    assert(ret == -1);

    /* Close everything */
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
