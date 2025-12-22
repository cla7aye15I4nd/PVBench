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

    for (int32_t jd = 73530872; jd <= 73530876; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);

        // Verify that the calendar reports the same Julian day after setting it
        status = U_ZERO_ERROR;
        int32_t jdOut = cal->get(UCAL_JULIAN_DAY, status);
        assert(U_SUCCESS(status));
        assert(jdOut == jd);

        // Get fields with status checks
        status = U_ZERO_ERROR;
        int32_t year = cal->get(UCAL_YEAR, status);
        assert(U_SUCCESS(status));

        status = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, status);
        assert(U_SUCCESS(status));

        status = U_ZERO_ERROR;
        int32_t day = cal->get(UCAL_DATE, status);
        assert(U_SUCCESS(status));

        // Semantic bounds checks
        assert(year >= minYear && year <= maxYear);
        assert(month >= minMonth && month <= maxMonth);
        assert(day >= minDate && day <= maxDate);

        // Additional logical consistency: month/day should be within reasonable ICU ranges
        // UCAL_MONTH is 0-based; ensure normalizer invariant holds
        assert(minMonth <= 0);
        assert(maxMonth >= 11);
        assert(minDate <= 1);
        assert(maxDate >= 28);
    }
    delete cal;
    return 0;
}