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

    // Validate calendar creation
    assert(U_SUCCESS(status));
    assert(calendar.isValid());

    // Semantic bounds: ERA range must be well-formed
    int32_t minEra = calendar->getMinimum(UCAL_ERA);
    int32_t maxEra = calendar->getMaximum(UCAL_ERA);
    assert(minEra <= maxEra);

    calendar->clear();

    // After clear, fields should be unset
    assert(calendar->isSet(UCAL_YEAR) == false);
    assert(calendar->isSet(UCAL_WEEK_OF_YEAR) == false);
    assert(calendar->isSet(UCAL_ERA) == false);

    // Set extreme/unusual values
    calendar->set(UCAL_YEAR, -2147483648);
    calendar->set(UCAL_WEEK_OF_YEAR, 33816240);

    // Reset status to specifically test the behavior of the get() call below
    status = U_ZERO_ERROR;
    int32_t era = calendar->get(UCAL_ERA, status);

    // Expected failure from dump.txt: status must be U_ILLEGAL_ARGUMENT_ERROR
    assert(status == U_ILLEGAL_ARGUMENT_ERROR);

    (void)era; // suppress unused variable warning; value is undefined on error
    return 0;
}