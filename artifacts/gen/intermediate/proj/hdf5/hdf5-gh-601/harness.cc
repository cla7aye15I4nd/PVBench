#include "hdf5.h"

#define LOG_LOCATION "cache_logging.out"

int main()
{
    hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
    H5Pset_fapl_core(fapl, 0, 0);
    H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0);
    H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0);
    H5Fclose(fapl);
    return 0;
}