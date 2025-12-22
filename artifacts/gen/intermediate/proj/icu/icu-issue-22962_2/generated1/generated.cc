#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=chinese"), status), status);
    assert(U_SUCCESS(status));
    assert(cal.getAlias() != nullptr);

    // First add should succeed
    status = U_ZERO_ERROR;
    cal->add(UCAL_DAY_OF_WEEK_IN_MONTH, 1661092210, status);
    assert(U_SUCCESS(status));
    // Semantic check: field value should be within valid range
    {
        int32_t minVal = cal->getMinimum(UCAL_DAY_OF_WEEK_IN_MONTH);
        int32_t maxVal = cal->getMaximum(UCAL_DAY_OF_WEEK_IN_MONTH);
        int32_t val = cal->get(UCAL_DAY_OF_WEEK_IN_MONTH, status);
        assert(U_SUCCESS(status));
        assert(val >= minVal && val <= maxVal);
    }

    // Second add should succeed
    status = U_ZERO_ERROR;
    cal->add(UCAL_MINUTE, -1330638081, status);
    assert(U_SUCCESS(status));
    // Semantic check: minute should be within [min, max]
    {
        int32_t minVal = cal->getMinimum(UCAL_MINUTE);
        int32_t maxVal = cal->getMaximum(UCAL_MINUTE);
        int32_t val = cal->get(UCAL_MINUTE, status);
        assert(U_SUCCESS(status));
        assert(val >= minVal && val <= maxVal);
    }

    // Third add is expected to fail per dump.txt
    status = U_ZERO_ERROR;
    cal->add(UCAL_MONTH, 643194, status);
    assert(U_FAILURE(status));

    return 0;
}