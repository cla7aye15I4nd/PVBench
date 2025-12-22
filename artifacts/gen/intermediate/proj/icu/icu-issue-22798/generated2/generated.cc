#include "unicode/msgfmt.h"
#include "unicode/utypes.h"
#include <cassert>

using namespace icu;

int main()
{
    UErrorCode status = U_ZERO_ERROR;
    // Initial state must be success before API calls
    assert(U_SUCCESS(status));

    UnicodeString pattern;
    constexpr static int testNestedLevel = 30000;
    for (int i = 0; i < testNestedLevel; i++) {
        pattern += u"A{0,choice,0#";
    }
    pattern += u"text";
    for (int i = 0; i < testNestedLevel; i++) {
        pattern += u"}a";
    }

    // Semantic check: ensure the constructed pattern length is exactly as expected
    // Each iteration adds 13 chars for "A{0,choice,0#" and 2 chars for "}a", plus 4 for "text"
    const int32_t expectedLen = testNestedLevel * 15 + 4; // 13 + 2 = 15 per level, plus 4
    assert(pattern.length() == expectedLen);

    // Construct MessageFormat and verify the expected failure status
    MessageFormat msg(pattern, status);
    assert(U_FAILURE(status));
    assert(status == U_INDEX_OUTOFBOUNDS_ERROR);

    return 0;
}