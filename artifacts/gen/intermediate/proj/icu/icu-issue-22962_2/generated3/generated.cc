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

    // First add: expect success
    cal->add(UCAL_DAY_OF_WEEK_IN_MONTH, 1661092210, status);
    assert(U_SUCCESS(status));
    {
        // Semantic check: value within valid range
        UErrorCode st = U_ZERO_ERROR;
        int32_t val = cal->get(UCAL_DAY_OF_WEEK_IN_MONTH, st);
        assert(U_SUCCESS(st));
        int32_t minV = cal->getMinimum(UCAL_DAY_OF_WEEK_IN_MONTH);
        int32_t maxV = cal->getMaximum(UCAL_DAY_OF_WEEK_IN_MONTH);
        assert(val >= minV && val <= maxV);
    }

    // Second add: expect success
    cal->add(UCAL_MINUTE, -1330638081, status);
    assert(U_SUCCESS(status));
    {
        // Semantic check: minute within valid range
        UErrorCode st = U_ZERO_ERROR;
        int32_t minute = cal->get(UCAL_MINUTE, st);
        assert(U_SUCCESS(st));
        int32_t minMinute = cal->getMinimum(UCAL_MINUTE);
        int32_t maxMinute = cal->getMaximum(UCAL_MINUTE);
        assert(minute >= minMinute && minute <= maxMinute);
    }

    // Third add: expected failure per dump.txt
    status = U_ZERO_ERROR; // ensure we capture failure from this call specifically
    cal->add(UCAL_MONTH, 643194, status);
    assert(U_FAILURE(status));

    // After failure, calendar object should still report valid field values when queried with a fresh status
    {
        UErrorCode st = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, st);
        assert(U_SUCCESS(st));
        int32_t minMonth = cal->getMinimum(UCAL_MONTH);
        int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
        assert(month >= minMonth && month <= maxMonth);
    }

    return 0;
}