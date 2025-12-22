#include <unicode/calendar.h>
#include <unicode/locid.h>

using namespace icu;

int main()
{
    const char* localeID = "bs_Cyrl@calendar=persian";
    UErrorCode status = U_ZERO_ERROR;
    Calendar* cal = Calendar::createInstance(Locale(localeID), status);
    for (int32_t jd = 67023580; jd <= 67023584; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);
        cal->get(UCAL_MONTH, status);
        cal->get(UCAL_DATE, status);
    }
    delete cal;
    return 0;
}