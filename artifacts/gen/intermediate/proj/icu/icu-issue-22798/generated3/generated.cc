#include "unicode/msgfmt.h"
#include "unicode/utypes.h"
#include "unicode/unistr.h"
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
    // Semantic check: partial length equals 13 * testNestedLevel (length of "A{0,choice,0#" is 13)
    assert(pattern.length() == 13 * testNestedLevel);

    pattern += u"text";
    // Semantic check: ensure the substring "text" exists
    int32_t posText = pattern.indexOf(u"text", 4);
    assert(posText >= 0);

    for (int i = 0; i < testNestedLevel; i++) {
        pattern += u"}a";
    }
    // Semantic check: final length equals 15 * testNestedLevel + 4 ("}a" is 2, plus 4 for "text")
    assert(pattern.length() == 15 * testNestedLevel + 4);
    // Check boundary characters
    assert(pattern.charAt(0) == u'A');
    assert(pattern.charAt(pattern.length() - 1) == u'a');

    // Status must start as success
    assert(status == U_ZERO_ERROR);

    // Constructing the MessageFormat with a deeply nested pattern should fail with U_INDEX_OUTOFBOUNDS_ERROR
    MessageFormat msg(pattern, status);
    assert(U_FAILURE(status));
    assert(status == U_INDEX_OUTOFBOUNDS_ERROR);

    return 0;
}