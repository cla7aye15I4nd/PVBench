#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/ucal.h"

using namespace icu;

int main()
{
    const char *localeID = "ar@calendar=islamic-civil";
    UErrorCode status = U_ZERO_ERROR;
    Calendar *cal = Calendar::createInstance(Locale(localeID), status);
    for (int32_t jd = 73530872; jd <= 73530876; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);
        cal->get(UCAL_YEAR, status);
        cal->get(UCAL_MONTH, status);
        cal->get(UCAL_DATE, status);
    }
    delete cal;
    return 0;
}