#include <assert.h>
#include "hdf5.h"

int main(int argc, char **argv)
{
    hid_t fid = H5Fopen(argv[1], H5F_ACC_RDONLY, H5P_DEFAULT);
    assert(fid >= 0);

    H5O_info_t oinfo;
    herr_t ret;

    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/soft_two", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(ret == -1);

    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/dsetA", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(ret == -1);

    H5E_BEGIN_TRY {
        ret = H5Oget_info_by_name(fid, "/soft_one", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;
    assert(ret == -1);

    herr_t ret_close = H5Fclose(fid);
    assert(ret_close >= 0);
    return 0;
}