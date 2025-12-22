#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/parseerr.h"
#include "unicode/rbnf.h"
#include <assert.h>

using namespace icu;

int main()
{
    UParseError perror;
    UErrorCode status = U_ZERO_ERROR;
    UnicodeString testStr(u"0110110/300113001103000113001103000110i/3013033:");
    RuleBasedNumberFormat rbfmt(testStr, Locale("as"), perror, status);
    assert(status == U_PARSE_ERROR);  // Number too large

    return 0;
}
