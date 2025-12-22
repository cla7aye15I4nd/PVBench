#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("tn-BW-u-ca-coptic"), status), status);

    // Creation must succeed
    assert(U_SUCCESS(status));
    assert(!calendar.isNull());

    // Basic semantic invariants for field ranges
    int32_t minMonth = calendar->getMinimum(UCAL_MONTH);
    int32_t maxMonth = calendar->getMaximum(UCAL_MONTH);
    assert(minMonth <= maxMonth);

    int32_t minOrdMonth = calendar->getMinimum(UCAL_ORDINAL_MONTH);
    int32_t maxOrdMonth = calendar->getMaximum(UCAL_ORDINAL_MONTH);
    assert(minOrdMonth <= maxOrdMonth);
    assert((maxOrdMonth - minOrdMonth) >= 0);

    calendar->clear();
    // Set a very large negative Julian day; set() has no status, so just perform it
    calendar->set(UCAL_JULIAN_DAY, -2147456654);

    // Expected failure: roll with huge amount should set U_ILLEGAL_ARGUMENT_ERROR
    status = U_ZERO_ERROR;
    calendar->roll(UCAL_ORDINAL_MONTH, 6910543, status);
    assert(status == U_ILLEGAL_ARGUMENT_ERROR); // as per dump.txt expectation
    assert(U_FAILURE(status));

    // After failure, the object should still be usable; recheck invariants that do not need status
    int32_t minOrdAfter = calendar->getMinimum(UCAL_ORDINAL_MONTH);
    int32_t maxOrdAfter = calendar->getMaximum(UCAL_ORDINAL_MONTH);
    assert(minOrdAfter <= maxOrdAfter);

    return 0;
}