#include "hdf5.h"

#define FILE_NAME "tid.h5"
#define DSET_NAME "Dataset 1"

static int test_appropriate_ids(void)
{
    hsize_t dims = 2;
    hid_t fcpl_id = H5Pcreate(H5P_FILE_CREATE);
    hid_t file_id = H5Fcreate(FILE_NAME, H5F_ACC_TRUNC, fcpl_id, H5P_DEFAULT);
    hid_t space_id = H5Screate_simple(1, &dims, NULL);
    hid_t dset_id = H5Dcreate2(file_id, DSET_NAME, H5T_NATIVE_INT, space_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);

    H5Pclose(fcpl_id);
    H5Sclose(space_id);
    H5Dclose(dset_id);
    H5Fclose(file_id);

    file_id = H5Fopen(FILE_NAME, H5F_ACC_RDONLY, H5P_DEFAULT);
    fcpl_id = H5Fget_create_plist(file_id);
    hid_t fapl_id = H5Fget_access_plist(file_id);
    dset_id = H5Dopen2(file_id, DSET_NAME, H5P_DEFAULT);

    H5E_BEGIN_TRY {
        H5Fget_create_plist(dset_id);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        H5Fget_access_plist(fapl_id);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        unsigned intent;
        H5Fget_intent(dset_id, &intent);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        unsigned long fileno = 0;
        H5Fget_fileno(dset_id, &fileno);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        H5Fget_freespace(dset_id);
    } H5E_END_TRY

    H5E_BEGIN_TRY {
        void *os_file_handle = NULL;
        H5Fget_vfd_handle(fapl_id, H5P_DEFAULT, &os_file_handle);
    } H5E_END_TRY

    H5Pclose(fapl_id);
    H5Pclose(fcpl_id);
    H5Dclose(dset_id);
    H5Fclose(file_id);

    return 0;
}

int main(void)
{
    test_appropriate_ids();
    return 0;
}