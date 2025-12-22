#include "hdf5.h"
#include <assert.h>

#define LOG_LOCATION "cache_logging.out"

int main()
{
    hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
    assert(fapl >= 0);

    assert(H5Pset_fapl_core(fapl, 0, 0) >= 0);
    assert(H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0) >= 0);

    // Ensure that setting the property twice doesn't cause problems
    assert(H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0) >= 0);

    assert(H5Pclose(fapl) >= 0);
    return 0;
}
