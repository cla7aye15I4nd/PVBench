#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include "unicode/localpointer.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=uddhist"), status), status);
    // Verify calendar creation succeeded
    assert(U_SUCCESS(status));
    assert(!cal.isNull());

    cal->clear();

    // Semantic checks: basic invariants for field bounds
    int32_t minW = cal->getMinimum(UCAL_WEEK_OF_YEAR);
    int32_t maxW = cal->getMaximum(UCAL_WEEK_OF_YEAR);
    assert(minW <= maxW);
    int32_t minY = cal->getMinimum(UCAL_YEAR);
    int32_t maxY = cal->getMaximum(UCAL_YEAR);
    assert(minY <= maxY);

    cal->set(UCAL_WEEK_OF_YEAR, 1666136);
    cal->set(UCAL_YEAR, -1887379272);

    // Expected failure: fieldDifference should set failure status
    UDate when = 261830011167902373443927125260580558779842815957727840993886210772873194951140935848493861585917165011373697198856398176256.000000;
    int32_t diff = cal->fieldDifference(when, UCAL_YEAR_WOY, status);
    (void)diff; // diff value is unspecified on failure; silence unused warning
    assert(U_FAILURE(status));

    return 0;
}
