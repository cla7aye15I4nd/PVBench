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
    assert(U_SUCCESS(status));

    for (int32_t i = 0; i < UCAL_FIELD_COUNT; i++) {
        UCalendarDateFields field = static_cast<UCalendarDateFields>(i);

        calendar->setTime(0, status);
        calendar->add(field, INT32_MAX / 2, status);
        calendar->add(field, INT32_MAX, status);
        bool shouldFailMax = (
            field == UCAL_ERA ||
            field == UCAL_YEAR ||
            field == UCAL_YEAR_WOY ||
            field == UCAL_EXTENDED_YEAR ||
            field == UCAL_IS_LEAP_MONTH ||
            field == UCAL_MONTH ||
            field == UCAL_ORDINAL_MONTH ||
            field == UCAL_ZONE_OFFSET ||
            field == UCAL_DST_OFFSET
        );
        if (shouldFailMax) {
            assert(U_FAILURE(status));
        }

        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        assert(U_SUCCESS(status));
        calendar->add(field, INT32_MIN / 2, status);
        calendar->add(field, INT32_MIN, status);
        bool shouldFailMin = (
            field == UCAL_YEAR ||
            field == UCAL_YEAR_WOY ||
            field == UCAL_EXTENDED_YEAR ||
            field == UCAL_IS_LEAP_MONTH ||
            field == UCAL_ZONE_OFFSET ||
            field == UCAL_DST_OFFSET
        );
        if (shouldFailMin) {
            assert(U_FAILURE(status));
        }
    }
    return 0;
}