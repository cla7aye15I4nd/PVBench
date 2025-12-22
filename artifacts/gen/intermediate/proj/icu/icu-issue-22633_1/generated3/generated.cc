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

        bool shouldFailMax = (
            i == UCAL_ERA || i == UCAL_YEAR || i == UCAL_YEAR_WOY ||
            i == UCAL_EXTENDED_YEAR || i == UCAL_IS_LEAP_MONTH ||
            i == UCAL_MONTH || i == UCAL_ORDINAL_MONTH ||
            i == UCAL_ZONE_OFFSET || i == UCAL_DST_OFFSET);
        if (shouldFailMax) {
            assert(U_FAILURE(status));
        }

        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN, status);

        bool shouldFailMin = (
            i == UCAL_YEAR || i == UCAL_YEAR_WOY || i == UCAL_EXTENDED_YEAR ||
            i == UCAL_IS_LEAP_MONTH || i == UCAL_ZONE_OFFSET || i == UCAL_DST_OFFSET);
        if (shouldFailMin) {
            assert(U_FAILURE(status));
        }
    }
    return 0;
}