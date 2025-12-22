#include "hdf5.h"
#include <assert.h>

#define FILE "temp2.h5"
#define GROUPNAME "./Data"

int main(void)
{
    // Create file
    hid_t file = H5Fcreate(FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file >= 0);

    // Create group
    hid_t grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(grpid >= 0);

    // Semantic check: verify the created object exists and is a group
    H5O_info2_t oinfo;
    herr_t ret = H5Oget_info_by_name(file, GROUPNAME, &oinfo, H5O_INFO_ALL, H5P_DEFAULT);
    assert(ret >= 0);
    assert(oinfo.type == H5O_TYPE_GROUP);

    // Expected failure: invalid source location for H5Gmove2
    H5E_BEGIN_TRY {
        ret = H5Gmove2(0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
    } H5E_END_TRY;
    assert(ret == -1); // Expected to fail

    // Close resources
    ret = H5Gclose(grpid);
    assert(ret >= 0);
    ret = H5Fclose(file);
    assert(ret >= 0);

    return 0;
}
