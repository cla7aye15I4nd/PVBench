#include "hdf5.h"
#include <assert.h>

#define FILE "temp2.h5"
#define GROUPNAME "./Data"

int main(void)
{
    hid_t file = H5Fcreate(FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file >= 0);

    hid_t grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(grpid >= 0);

    // Semantic check: verify the created group exists and is of type group
    H5O_info2_t oinfo_before;
    herr_t ret_info_before = H5Oget_info_by_name(file, GROUPNAME, &oinfo_before, H5O_INFO_ALL, H5P_DEFAULT);
    assert(ret_info_before >= 0);
    assert(oinfo_before.type == H5O_TYPE_GROUP);

    // Expected failure: invalid source location for H5Gmove2
    herr_t ret;
    H5E_BEGIN_TRY {
        ret = H5Gmove2(0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
    } H5E_END_TRY;
    assert(ret == -1); // Expected to fail with invalid source location

    // Semantic check: destination should not exist after failed move
    H5O_info2_t oinfo_dest;
    herr_t ret_dest;
    H5E_BEGIN_TRY {
        ret_dest = H5Oget_info_by_name(file, "./Data_link/Data_new1/CData", &oinfo_dest, H5O_INFO_ALL, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(ret_dest < 0);

    // Semantic check: original created group should still exist and be a group
    H5O_info2_t oinfo_after;
    herr_t ret_info_after = H5Oget_info_by_name(file, GROUPNAME, &oinfo_after, H5O_INFO_ALL, H5P_DEFAULT);
    assert(ret_info_after >= 0);
    assert(oinfo_after.type == H5O_TYPE_GROUP);

    herr_t ret_close_grp = H5Gclose(grpid);
    assert(ret_close_grp >= 0);

    herr_t ret_close_file = H5Fclose(file);
    assert(ret_close_file >= 0);
    return 0;
}