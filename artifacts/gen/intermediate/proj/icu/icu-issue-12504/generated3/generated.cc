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

    // Establish valid ranges for semantic checks
    int32_t minMonth = cal->getMinimum(UCAL_MONTH);
    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t minDate  = cal->getMinimum(UCAL_DATE);
    int32_t maxDate  = cal->getMaximum(UCAL_DATE);
    assert(minMonth <= maxMonth);
    assert(minDate <= maxDate);

    for (int32_t jd = 67023580; jd <= 67023584; jd++) {
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);

        // Verify the Julian day was set correctly
        status = U_ZERO_ERROR;
        int32_t jd_back = cal->get(UCAL_JULIAN_DAY, status);
        assert(U_SUCCESS(status));
        assert(jd_back == jd);

        // Get month and check status and bounds
        status = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, status);
        assert(U_SUCCESS(status));
        assert(month >= minMonth && month <= maxMonth);

        // Get date and check status and bounds
        status = U_ZERO_ERROR;
        int32_t date = cal->get(UCAL_DATE, status);
        assert(U_SUCCESS(status));
        assert(date >= minDate && date <= maxDate);
    }
    delete cal;
    return 0;
}