#include "unicode/calendar.h"
#include "unicode/timezone.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    Locale locale("ckb_IQ@calendar=ethiopic-amete-alem");
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(
            *TimeZone::getGMT(), locale, status));
    cal->clear();
    status = U_ZERO_ERROR;
    int32_t ret0 = cal->fieldDifference(
        (double)115177509667085876226560460721710683457425563915331054206329829993967720136006086546037257220523631494518538798239249720325557586193565921621016454170342731307548672.0,
        UCAL_MONTH, status);
    (void)ret0;
    status = U_ZERO_ERROR;
    cal->set(UCAL_DAY_OF_WEEK_IN_MONTH, -2111799174);
    cal->add(UCAL_ERA, -1426056846, status);
    assert(U_FAILURE(status));
    return 0;
}