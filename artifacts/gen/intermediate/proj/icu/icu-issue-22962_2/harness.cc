#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=chinese"), status), status);
    cal->add(UCAL_DAY_OF_WEEK_IN_MONTH, 1661092210, status);
    cal->add(UCAL_MINUTE, -1330638081, status);
    cal->add(UCAL_MONTH, 643194, status);
    return 0;
}