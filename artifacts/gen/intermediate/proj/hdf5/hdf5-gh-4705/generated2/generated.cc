#include "hdf5.h"
#include <assert.h>

int main(int argc, char **argv)
{
    H5L_info2_t linfo;

    hid_t dtype = H5Tcopy(H5T_NATIVE_INT);
    assert(dtype >= 0);

    herr_t ret;
    H5E_BEGIN_TRY {
        ret = H5Lget_info2(dtype, argv[1], &linfo, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(ret == -1); // Expected failure per dump.txt

    herr_t cclose = H5Tclose(dtype);
    assert(cclose >= 0);

    return 0;
}