#include "hdf5.h"
#include <cassert>

#define FILE "temp2.h5"
#define GROUPNAME "./Data"

int main(void)
{
    // Create file and verify success
    hid_t file = H5Fcreate(FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file >= 0);

    // Create group and verify success
    hid_t grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(grpid >= 0);

    // Semantic: Verify the created object exists and is a group
    H5O_info2_t oinfo;
    herr_t status = H5Oget_info_by_name(file, GROUPNAME, &oinfo, H5O_INFO_BASIC, H5P_DEFAULT);
    assert(status >= 0);
    assert(oinfo.type == H5O_TYPE_GROUP);

    // Expected failure: invalid source location in H5Gmove2
    herr_t ret;
    H5E_BEGIN_TRY {
        ret = H5Gmove2(0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
    } H5E_END_TRY;
    assert(ret == -1);

    // Semantic: Destination should not exist after failed move
    herr_t info_ret;
    H5E_BEGIN_TRY {
        info_ret = H5Oget_info_by_name(file, "./Data_link/Data_new1/CData", &oinfo, H5O_INFO_BASIC, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(info_ret < 0);

    // Semantic: Original group should still exist and be a group
    status = H5Oget_info_by_name(file, GROUPNAME, &oinfo, H5O_INFO_BASIC, H5P_DEFAULT);
    assert(status >= 0);
    assert(oinfo.type == H5O_TYPE_GROUP);

    // Close resources and verify success
    herr_t c_ret = H5Gclose(grpid);
    assert(c_ret >= 0);
    c_ret = H5Fclose(file);
    assert(c_ret >= 0);

    return 0;
}
