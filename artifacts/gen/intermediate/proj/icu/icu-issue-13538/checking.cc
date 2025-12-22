#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/ucal.h"
#include <assert.h>

using namespace icu;

int main()
{
    const char *localeID = "ar@calendar=islamic-civil";
    UErrorCode status = U_ZERO_ERROR;
    Calendar *cal = Calendar::createInstance(Locale(localeID), status);
    assert(U_SUCCESS(status));

    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t maxDayOfMonth = cal->getMaximum(UCAL_DATE);
    int32_t year, month, dayOfMonth;

    for (int32_t jd = 73530872; jd <= 73530876; jd++) {
        status = U_ZERO_ERROR;
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);
        year = cal->get(UCAL_YEAR, status);
        month = cal->get(UCAL_MONTH, status);
        dayOfMonth = cal->get(UCAL_DATE, status);
        assert(U_SUCCESS(status));
        assert(month <= maxMonth && dayOfMonth <= maxDayOfMonth);
    }

    delete cal;
    return 0;
}