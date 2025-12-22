#include "unicode/msgfmt.h"
#include "unicode/utypes.h"
#include <assert.h>

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
    MessageFormat msg(pattern, status);
    assert(status == U_INDEX_OUTOFBOUNDS_ERROR);  // Deep nested choice should cause error but not crash

    return 0;
}
