#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/parseerr.h"
#include "unicode/rbnf.h"
#include <cassert>

using namespace icu;

int main()
{
    UParseError perror; // will be filled on parse error
    UErrorCode status = U_ZERO_ERROR;
    UnicodeString testStr(u"0110110/300113001103000113001103000110i/3013033:");
    RuleBasedNumberFormat rbfmt(testStr, Locale("as"), perror, status);

    // Expected failure: parsing rules should fail with U_PARSE_ERROR
    assert(U_FAILURE(status));
    assert(status == U_PARSE_ERROR);

    // Semantic checks: parse error offset should be within the bounds of the rule string
    int32_t len = testStr.length();
    assert(perror.offset >= 0);
    assert(perror.offset <= len);

    return 0;
}