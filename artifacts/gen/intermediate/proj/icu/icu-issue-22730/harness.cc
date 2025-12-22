#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> calendar(
        Calendar::createInstance(Locale("tn-BW-u-ca-coptic"), status), status);
    calendar->clear();
    calendar->set(UCAL_JULIAN_DAY, -2147456654);
    calendar->roll(UCAL_ORDINAL_MONTH, 6910543, status);
    return 0;
}