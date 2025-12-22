#include "hdf5.h"

int main(int argc, char **argv)
{
    H5L_info2_t linfo;
    H5Lget_info2(H5Tcopy(H5T_NATIVE_INT), argv[1], &linfo, H5P_DEFAULT);
    return 0;
}