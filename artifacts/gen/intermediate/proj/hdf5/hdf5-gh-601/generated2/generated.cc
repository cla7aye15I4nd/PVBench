#include "hdf5.h"
#include <assert.h>

#define LOG_LOCATION "cache_logging.out"

int main()
{
    hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
    assert(fapl >= 0);

    herr_t ret;

    ret = H5Pset_fapl_core(fapl, 0, 0);
    assert(ret >= 0);

    ret = H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0);
    assert(ret >= 0);

    // Re-applying the same logging options should still succeed
    ret = H5Pset_mdc_log_options(fapl, 1, LOG_LOCATION, 0);
    assert(ret >= 0);

    // Semantic sanity check: log location string should be non-empty
    assert(LOG_LOCATION[0] != '\0');

    ret = H5Pclose(fapl);
    assert(ret >= 0);
    return 0;
}