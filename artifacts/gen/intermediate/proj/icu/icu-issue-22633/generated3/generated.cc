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
    // Verify calendar creation succeeded
    assert(U_SUCCESS(status));
    assert(cal.getAlias() != nullptr);

    // Basic semantic invariant: min <= max for YEAR
    int32_t minYearBound = cal->getMinimum(UCAL_YEAR);
    int32_t maxYearBound = cal->getMaximum(UCAL_YEAR);
    assert(minYearBound <= maxYearBound);

    cal->setTime(
        2043071457431218011677338081118001787485161156097100985923226601036925437809699842362992455895409920480414647512899096575018732258582416938813614617757317338664031880042592085084690242819214720523061081124318514531466365480449329351434046537728.000000,
        status);
    // Expected to succeed per dump.txt
    assert(U_SUCCESS(status));

    // After successful setTime, fields should be within valid ranges
    {
        UErrorCode tmp = U_ZERO_ERROR;
        int32_t month = cal->get(UCAL_MONTH, tmp);
        assert(U_SUCCESS(tmp));
        int32_t minMonth = cal->getMinimum(UCAL_MONTH);
        int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
        assert(minMonth <= maxMonth);
        assert(month >= minMonth && month <= maxMonth);

        tmp = U_ZERO_ERROR;
        int32_t date = cal->get(UCAL_DATE, tmp);
        assert(U_SUCCESS(tmp));
        int32_t minDate = cal->getMinimum(UCAL_DATE);
        int32_t maxDate = cal->getMaximum(UCAL_DATE);
        assert(minDate <= maxDate);
        assert(date >= minDate && date <= maxDate);
    }

    cal->set(UCAL_EXTENDED_YEAR, -1594662558);

    int32_t year = cal->get(UCAL_YEAR, status);
    // Expected to succeed per dump.txt
    assert(U_SUCCESS(status));
    // YEAR should be within defined bounds
    assert(year >= minYearBound && year <= maxYearBound);

    cal->setTime(
        17000065021099877464213620139773683829419175940649608600213244013003611130029599692535053209683880603725167923910423116397083334648012657787978113960494455603744210944.000000,
        status);
    // Expected to succeed per dump.txt
    assert(U_SUCCESS(status));

    // Expected failure case (dump.txt line 24)
    cal->add(UCAL_YEAR, 1935762034, status);
    assert(U_FAILURE(status));

    status = U_ZERO_ERROR;
    cal->set(UCAL_ERA, 1651667877);

    // Expected failure case (dump.txt line 29)
    cal->add(UCAL_YEAR, 1935762034, status);
    assert(U_FAILURE(status));

    return 0;
}