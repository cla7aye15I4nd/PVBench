#include <cassert>
#include <climits>
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("nds-NL-u-ca-islamic-umalqura"), status),
        status);

    // Verify calendar creation succeeded
    assert(U_SUCCESS(status));
    assert(calendar.getAlias() != nullptr);

    // Semantic invariants: field bounds should be sensible
    int32_t eraMin = calendar->getMinimum(UCAL_ERA);
    int32_t eraMax = calendar->getMaximum(UCAL_ERA);
    assert(eraMin <= eraMax);

    int32_t weekMax = calendar->getMaximum(UCAL_WEEK_OF_YEAR);
    int32_t yearMin = calendar->getMinimum(UCAL_YEAR);
    assert(weekMax >= 0);
    assert(yearMin > INT_MIN); // Calendar should not support INT_MIN as a valid year

    calendar->clear();
    calendar->set(UCAL_YEAR, -2147483648);
    calendar->set(UCAL_WEEK_OF_YEAR, 33816240);

    // Ensure we indeed provided an out-of-range week value
    assert(33816240 > weekMax);

    // Expected failure: get(UCAL_ERA, status) should set illegal argument error
    status = U_ZERO_ERROR;
    int32_t era = calendar->get(UCAL_ERA, status);
    (void)era; // return value is undefined on failure; silence unused warning
    assert(status == U_ILLEGAL_ARGUMENT_ERROR);

    return 0;
}
