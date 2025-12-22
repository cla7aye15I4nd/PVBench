#include "unicode/msgfmt.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    UnicodeString pattern;
    constexpr static int testNestedLevel = 30000;
    for (int i = 0; i < testNestedLevel; i++) {
        pattern += u"A{0,choice,0#";
    }
    pattern += u"text";
    for (int i = 0; i < testNestedLevel; i++) {
        pattern += u"}a";
    }

    // Semantic check: ensure we constructed the intended pattern size
    // Each loop adds 13 code units ("A{0,choice,0#") and later 2 code units ("}a").
    // Total = 15 * testNestedLevel + 4 (for "text").
    auto expectedLen = testNestedLevel * 15 + 4;
    assert(pattern.length() == expectedLen);

    // Precondition: status should be clean before calling the API
    assert(status == U_ZERO_ERROR);

    // Expected failure: deep nested choice should produce U_INDEX_OUTOFBOUNDS_ERROR
    MessageFormat msg(pattern, status);
    assert(U_FAILURE(status));
    assert(status == U_INDEX_OUTOFBOUNDS_ERROR);

    return 0;
}