#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("en-u-ca-japanese"), status), status);
    assert(U_SUCCESS(status));

    calendar->clear();
    calendar->roll(UCAL_EXTENDED_YEAR, -1946156856, status);
    assert(status == U_ILLEGAL_ARGUMENT_ERROR);
    return 0;
}