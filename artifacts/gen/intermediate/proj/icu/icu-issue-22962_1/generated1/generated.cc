#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=uddhist"), status), status);
    assert(U_SUCCESS(status));
    assert(!cal.isNull());

    cal->clear();

    // Basic semantic invariants for fields
    int32_t minW = cal->getMinimum(UCAL_WEEK_OF_YEAR);
    int32_t maxW = cal->getMaximum(UCAL_WEEK_OF_YEAR);
    assert(minW <= maxW);
    int32_t minYear = cal->getMinimum(UCAL_YEAR);
    int32_t maxYear = cal->getMaximum(UCAL_YEAR);
    assert(minYear <= maxYear);

    cal->set(UCAL_WEEK_OF_YEAR, 1666136);
    cal->set(UCAL_YEAR, -1887379272);

    // The following call is expected to fail per dump.txt
    status = U_ZERO_ERROR;
    int32_t diff = cal->fieldDifference(
        261830011167902373443927125260580558779842815957727840993886210772873194951140935848493861585917165011373697198856398176256.000000,
        UCAL_YEAR_WOY, status);
    (void)diff; // value unspecified on failure; avoid unused warning
    assert(U_FAILURE(status));
    return 0;
}