#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("en"), status), status);
    for (int32_t i = 0; i < UCAL_FIELD_COUNT; i++) {
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX, status);
        {
            bool expectFailMax = false;
            expectFailMax = expectFailMax || (i == UCAL_ERA);
            expectFailMax = expectFailMax || (i == UCAL_YEAR);
            expectFailMax = expectFailMax || (i == UCAL_YEAR_WOY);
            expectFailMax = expectFailMax || (i == UCAL_EXTENDED_YEAR);
            expectFailMax = expectFailMax || (i == UCAL_IS_LEAP_MONTH);
            expectFailMax = expectFailMax || (i == UCAL_MONTH);
    #ifdef UCAL_ORDINAL_MONTH
            expectFailMax = expectFailMax || (i == UCAL_ORDINAL_MONTH);
    #endif
            expectFailMax = expectFailMax || (i == UCAL_ZONE_OFFSET);
            expectFailMax = expectFailMax || (i == UCAL_DST_OFFSET);
            if (expectFailMax) {
                assert(U_FAILURE(status));
            }
        }

        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN, status);
        {
            bool expectFailMin = false;
            expectFailMin = expectFailMin || (i == UCAL_YEAR);
            expectFailMin = expectFailMin || (i == UCAL_YEAR_WOY);
            expectFailMin = expectFailMin || (i == UCAL_EXTENDED_YEAR);
            expectFailMin = expectFailMin || (i == UCAL_IS_LEAP_MONTH);
            expectFailMin = expectFailMin || (i == UCAL_ZONE_OFFSET);
            expectFailMin = expectFailMin || (i == UCAL_DST_OFFSET);
            if (expectFailMin) {
                assert(U_FAILURE(status));
            }
        }
    }
    return 0;
}