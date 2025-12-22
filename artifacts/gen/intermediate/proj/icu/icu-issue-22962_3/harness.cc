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
    calendar->clear();
    calendar->set(UCAL_YEAR, -2147483648);
    calendar->set(UCAL_WEEK_OF_YEAR, 33816240);
    calendar->get(UCAL_ERA, status);
    return 0;
}