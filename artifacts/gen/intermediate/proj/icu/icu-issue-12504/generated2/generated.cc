#include <unicode/calendar.h>
#include <unicode/locid.h>
#include <cassert>

using namespace icu;

int main()
{
    const char* localeID = "bs_Cyrl@calendar=persian";
    UErrorCode status = U_ZERO_ERROR;
    Calendar* cal = Calendar::createInstance(Locale(localeID), status);
    assert(cal != nullptr);
    assert(U_SUCCESS(status));

    // Retrieve invariant bounds for semantic checks
    int32_t minMonth = cal->getMinimum(UCAL_MONTH);
    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t minDate = cal->getMinimum(UCAL_DATE);
    int32_t maxDate = cal->getMaximum(UCAL_DATE);
    int32_t minDOW  = cal->getMinimum(UCAL_DAY_OF_WEEK);
    int32_t maxDOW  = cal->getMaximum(UCAL_DAY_OF_WEEK);

    // Basic invariants on bounds
    assert(minMonth <= maxMonth);
    assert(minDate <= maxDate);
    assert(minDOW  <= maxDOW);

    for (int32_t jd = 67023580; jd <= 67023584; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);

        // Get and validate month
        status = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, status);
        assert(U_SUCCESS(status));
        assert(month >= minMonth && month <= maxMonth);

        // Get and validate date (day of month)
        status = U_ZERO_ERROR;
        int32_t date = cal->get(UCAL_DATE, status);
        assert(U_SUCCESS(status));
        assert(date >= minDate && date <= maxDate);

        // Additional semantic: day of week within its bounds
        status = U_ZERO_ERROR;
        int32_t dow = cal->get(UCAL_DAY_OF_WEEK, status);
        assert(U_SUCCESS(status));
        assert(dow >= minDOW && dow <= maxDOW);
    }

    delete cal;
    return 0;
}