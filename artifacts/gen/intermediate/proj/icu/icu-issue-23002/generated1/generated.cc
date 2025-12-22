#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/parseerr.h"
#include "unicode/rbnf.h"
#include <cassert>
#include <cstring>

using namespace icu;

int main()
{
    // Initialize parse error structure to avoid reading uninitialized fields
    UParseError perror;
    std::memset(&perror, 0, sizeof(perror));

    UErrorCode status = U_ZERO_ERROR;
    UnicodeString testStr(u"0110110/300113001103000113001103000110i/3013033:");

    // Basic semantic sanity check on input
    assert(testStr.length() > 0);

    RuleBasedNumberFormat rbfmt(testStr, Locale("as"), perror, status);

    // Expected failure from dump.txt: status should indicate a parse error
    assert(U_FAILURE(status));
    assert(status == U_PARSE_ERROR);

    // Additional semantic checks for error reporting
    // At least one of line/offset should be non-negative on parse error
    assert(perror.offset >= 0 || perror.line >= 0);
    // Ensure error context buffers are properly NUL-terminated within bounds
    assert(perror.preContext[U_PARSE_CONTEXT_LEN - 1] == 0);
    assert(perror.postContext[U_PARSE_CONTEXT_LEN - 1] == 0);

    return 0;
}
