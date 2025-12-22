#include "hdf5.h"
#include <assert.h>

#define FILE "temp2.h5"
#define GROUPNAME "./Data"

int main(void)
{
    hid_t file = H5Fcreate(FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    assert(file != -1);

    hid_t grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    assert(grpid != -1);

    // Test H5Gmove2 with invalid ID - should fail
    herr_t ret;
    H5E_BEGIN_TRY {
        ret = H5Gmove2(0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
    } H5E_END_TRY
    assert(ret == -1);  // Expected to fail with invalid source location

    assert(H5Gclose(grpid) != -1);
    assert(H5Fclose(file) != -1);

    return 0;
}
