#include "hdf5.h"

int main(int argc, char **argv)
{
    hid_t fid = H5Fopen(argv[1], H5F_ACC_RDONLY, H5P_DEFAULT);
    H5O_info_t oinfo;

    H5E_BEGIN_TRY {
        H5Oget_info_by_name(fid, "/soft_two", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;

    H5E_BEGIN_TRY {
        H5Oget_info_by_name(fid, "/dsetA", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;

    H5E_BEGIN_TRY {
        H5Oget_info_by_name(fid, "/soft_one", &oinfo, H5P_DEFAULT);
    } H5E_END_TRY;

    H5Fclose(fid);
    return 0;
}