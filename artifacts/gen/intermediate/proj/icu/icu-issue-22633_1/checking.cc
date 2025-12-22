#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <assert.h>
#include <climits>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(Calendar::createInstance(Locale("en"), status), status);
    assert(U_SUCCESS(status));

    for (int32_t i = 0; i < UCAL_FIELD_COUNT; i++) {
        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MAX, status);

        if ((i == UCAL_ERA) || (i == UCAL_YEAR) || (i == UCAL_YEAR_WOY) ||
            (i == UCAL_EXTENDED_YEAR) || (i == UCAL_IS_LEAP_MONTH) ||
            (i == UCAL_MONTH) || (i == UCAL_ORDINAL_MONTH) ||
            (i == UCAL_ZONE_OFFSET) || (i == UCAL_DST_OFFSET)) {
            assert(U_FAILURE(status));  // add INT32_MAX should fail
        } else {
            assert(U_SUCCESS(status));  // add INT32_MAX should still success
        }

        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN, status);

        if ((i == UCAL_YEAR) || (i == UCAL_YEAR_WOY) || (i == UCAL_EXTENDED_YEAR) ||
            (i == UCAL_IS_LEAP_MONTH) || (i == UCAL_ZONE_OFFSET) || (i == UCAL_DST_OFFSET)) {
            assert(U_FAILURE(status));  // add INT32_MIN should fail
        } else {
            assert(U_SUCCESS(status));  // add INT32_MIN should still success
        }
    }
    return 0;
}