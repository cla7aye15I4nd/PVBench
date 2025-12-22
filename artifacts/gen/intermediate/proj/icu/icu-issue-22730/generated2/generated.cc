#include <cassert>
#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("tn-BW-u-ca-coptic"), status), status);

    // Verify calendar creation succeeded
    assert(U_SUCCESS(status));
    assert(calendar.getAlias() != nullptr);

    // Semantic check: bounds for the field we will roll
    int32_t minOrdinal = calendar->getMinimum(UCAL_ORDINAL_MONTH);
    int32_t maxOrdinal = calendar->getMaximum(UCAL_ORDINAL_MONTH);
    assert(minOrdinal <= maxOrdinal);

    calendar->clear();
    calendar->set(UCAL_JULIAN_DAY, -2147456654);

    // Reset status before operation under test
    status = U_ZERO_ERROR;
    calendar->roll(UCAL_ORDINAL_MONTH, 6910543, status);

    // Expected failure according to dump: should set U_ILLEGAL_ARGUMENT_ERROR
    assert(status == U_ILLEGAL_ARGUMENT_ERROR);

    // Ensure the object remains usable after failure once status is reset
    status = U_ZERO_ERROR;
    int32_t minOrdinal2 = calendar->getMinimum(UCAL_ORDINAL_MONTH);
    int32_t maxOrdinal2 = calendar->getMaximum(UCAL_ORDINAL_MONTH);
    assert(minOrdinal2 == minOrdinal);
    assert(maxOrdinal2 == maxOrdinal);

    return 0;
}