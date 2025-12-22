#include "hdf5.h"

#define FILE "temp2.h5"
#define GROUPNAME "./Data"

int main(void)
{
    hid_t file = H5Fcreate(FILE, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    hid_t grpid = H5Gcreate2(file, GROUPNAME, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    H5Gmove2(0, "./Soft2/CData", file, "./Data_link/Data_new1/CData");
    H5Gclose(grpid);
    H5Fclose(file);
    return 0;
}