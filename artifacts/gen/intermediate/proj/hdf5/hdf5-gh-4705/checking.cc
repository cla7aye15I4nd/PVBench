#include "hdf5.h"
#include <assert.h>

int main(int argc, char **argv)
{
    H5L_info2_t linfo;

    hid_t dtype = H5Tcopy(H5T_NATIVE_INT);
    assert(dtype != -1);

    // Test passing a datatype ID to H5Lget_info2, it should not fail
    assert(H5Lget_info2(dtype, argv[1], &linfo, H5P_DEFAULT) != -1);

    assert(H5Tclose(dtype) != -1);

    return 0;
}
