#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"

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

        status = U_ZERO_ERROR;
        calendar->setTime(0, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN / 2, status);
        calendar->add(static_cast<UCalendarDateFields>(i), INT32_MIN, status);
    }
    return 0;
}