#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("nds-NL-u-ca-islamic-umalqura"), status),
        status);

    // Creation should succeed
    assert(U_SUCCESS(status));
    assert(calendar.getAlias() != nullptr);

    // Semantic checks on ranges for fields we will use
    int32_t minYear = calendar->getMinimum(UCAL_YEAR);
    int32_t maxYear = calendar->getMaximum(UCAL_YEAR);
    assert(minYear <= maxYear);

    int32_t minWeek = calendar->getMinimum(UCAL_WEEK_OF_YEAR);
    int32_t maxWeek = calendar->getMaximum(UCAL_WEEK_OF_YEAR);
    assert(minWeek <= maxWeek);

    int32_t minEra = calendar->getMinimum(UCAL_ERA);
    int32_t maxEra = calendar->getMaximum(UCAL_ERA);
    assert(minEra <= maxEra);

    calendar->clear();

    // Set extreme/invalid values
    calendar->set(UCAL_YEAR, -2147483648);
    calendar->set(UCAL_WEEK_OF_YEAR, 33816240);

    // The values we set are far outside valid ranges, ensure that is indeed so
    assert(33816240 > maxWeek);
    // Likely outside valid year range as well
    assert(-2147483648 < minYear);

    // Expected failure: get(UCAL_ERA, ...) should set status to U_ILLEGAL_ARGUMENT_ERROR
    status = U_ZERO_ERROR; // ensure clean status before the call
    int32_t era = calendar->get(UCAL_ERA, status);
    (void)era; // value is undefined on error, but ensure no overflow/crash occurred
    assert(U_FAILURE(status));
    assert(status == U_ILLEGAL_ARGUMENT_ERROR);

    return 0;
}