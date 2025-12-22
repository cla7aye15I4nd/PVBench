#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include <assert.h>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=uddhist"), status), status);
    assert(U_SUCCESS(status));

    cal->clear();
    cal->set(UCAL_WEEK_OF_YEAR, 1666136);
    cal->set(UCAL_YEAR, -1887379272);
    cal->fieldDifference(
        261830011167902373443927125260580558779842815957727840993886210772873194951140935848493861585917165011373697198856398176256.000000,
        UCAL_YEAR_WOY, status);
    assert(U_FAILURE(status));  // Should return failure

    return 0;
}
