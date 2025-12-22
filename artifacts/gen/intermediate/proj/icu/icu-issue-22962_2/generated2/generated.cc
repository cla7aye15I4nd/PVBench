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
    assert(cal.isValid());

    // Add a very large number of weeks-in-month; expect success
    cal->add(UCAL_DAY_OF_WEEK_IN_MONTH, 1661092210, status);
    assert(U_SUCCESS(status));
    // Semantic check: field value should be within valid range
    {
        UErrorCode tmpStatus = U_ZERO_ERROR;
        int32_t val = cal->get(UCAL_DAY_OF_WEEK_IN_MONTH, tmpStatus);
        assert(U_SUCCESS(tmpStatus));
        int32_t minV = cal->getMinimum(UCAL_DAY_OF_WEEK_IN_MONTH);
        int32_t maxV = cal->getMaximum(UCAL_DAY_OF_WEEK_IN_MONTH);
        assert(val >= minV && val <= maxV);
    }

    // Add a large negative number of minutes; expect success
    cal->add(UCAL_MINUTE, -1330638081, status);
    assert(U_SUCCESS(status));
    // Semantic check: minute should be within valid range
    {
        UErrorCode tmpStatus = U_ZERO_ERROR;
        int32_t minute = cal->get(UCAL_MINUTE, tmpStatus);
        assert(U_SUCCESS(tmpStatus));
        int32_t minMinute = cal->getMinimum(UCAL_MINUTE);
        int32_t maxMinute = cal->getMaximum(UCAL_MINUTE);
        assert(minute >= minMinute && minute <= maxMinute);
    }

    // Expected failure: extremely large month addition should fail per dump.txt
    cal->add(UCAL_MONTH, 643194, status);
    assert(U_FAILURE(status));

    return 0;
}
