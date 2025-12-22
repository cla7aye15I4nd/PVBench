#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/ucal.h"
#include <cassert>

using namespace icu;

int main()
{
    const char *localeID = "ar@calendar=islamic-civil";
    UErrorCode status = U_ZERO_ERROR;
    Calendar *cal = Calendar::createInstance(Locale(localeID), status);
    assert(U_SUCCESS(status));
    assert(cal != nullptr);

    // Establish field bounds for semantic checks
    int32_t minYear = cal->getMinimum(UCAL_YEAR);
    int32_t maxYear = cal->getMaximum(UCAL_YEAR);
    int32_t minMonth = cal->getMinimum(UCAL_MONTH);
    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t minDate = cal->getMinimum(UCAL_DATE);
    int32_t maxDate = cal->getMaximum(UCAL_DATE);

    assert(minYear <= maxYear);
    assert(minMonth <= maxMonth);
    assert(minDate <= maxDate);

    for (int32_t jd = 73530872; jd <= 73530876; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);

        // YEAR
        status = U_ZERO_ERROR;
        int32_t year = cal->get(UCAL_YEAR, status);
        assert(U_SUCCESS(status));
        assert(year >= minYear && year <= maxYear);

        // MONTH
        status = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, status);
        assert(U_SUCCESS(status));
        assert(month >= minMonth && month <= maxMonth);

        // DATE (day of month)
        status = U_ZERO_ERROR;
        int32_t date = cal->get(UCAL_DATE, status);
        assert(U_SUCCESS(status));
        assert(date >= minDate && date <= maxDate);

        // Semantic consistency: the julian day we set should be retrievable
        status = U_ZERO_ERROR;
        int32_t jd_out = cal->get(UCAL_JULIAN_DAY, status);
        assert(U_SUCCESS(status));
        assert(jd_out == jd);

        (void)year;  // Suppress unused variable warnings if asserts are compiled out
        (void)month;
        (void)date;
    }
    delete cal;
    return 0;
}