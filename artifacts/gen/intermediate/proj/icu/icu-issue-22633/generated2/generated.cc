#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(
        Calendar::createInstance(Locale("en@calendar=chinese"), status), status);
    assert(U_SUCCESS(status));
    assert(cal.getAlias() != nullptr);

    cal->setTime(
        2043071457431218011677338081118001787485161156097100985923226601036925437809699842362992455895409920480414647512899096575018732258582416938813614617757317338664031880042592085084690242819214720523061081124318514531466365480449329351434046537728.000000,
        status);
    assert(U_SUCCESS(status));

    cal->set(UCAL_EXTENDED_YEAR, -1594662558);

    int32_t year = cal->get(UCAL_YEAR, status);
    assert(U_SUCCESS(status));
    int32_t minYear = cal->getMinimum(UCAL_YEAR);
    int32_t maxYear = cal->getMaximum(UCAL_YEAR);
    assert(year >= minYear);
    assert(year <= maxYear);

    cal->setTime(
        17000065021099877464213620139773683829419175940649608600213244013003611130029599692535053209683880603725167923910423116397083334648012657787978113960494455603744210944.000000,
        status);
    assert(U_SUCCESS(status));

    cal->add(UCAL_YEAR, 1935762034, status);
    assert(U_FAILURE(status)); // Expected failure per dump.txt

    status = U_ZERO_ERROR;
    cal->set(UCAL_ERA, 1651667877);
    cal->add(UCAL_YEAR, 1935762034, status);
    assert(U_FAILURE(status)); // Expected failure per dump.txt

    return 0;
}