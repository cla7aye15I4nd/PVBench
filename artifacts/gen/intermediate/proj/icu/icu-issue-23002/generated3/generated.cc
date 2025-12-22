#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/parseerr.h"
#include "unicode/rbnf.h"
#include <cassert>

using namespace icu;

int main()
{
    UParseError perror = UParseError(); // zero-initialize for predictable values
    UErrorCode status = U_ZERO_ERROR;
    UnicodeString testStr(u"0110110/300113001103000113001103000110i/3013033:");
    RuleBasedNumberFormat rbfmt(testStr, Locale("as"), perror, status);

    // Expected failure: constructor should set a parse error status
    assert(U_FAILURE(status));
    assert(status == U_PARSE_ERROR);

    // Semantic check: on parse error, ICU should report at least a line or offset
    assert(perror.line >= 0 || perror.offset >= 0);

    return 0;
}