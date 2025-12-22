#include "unicode/uregex.h"
#include "unicode/ustring.h"
#include <cassert>

using namespace icu;

int main()
{
    UnicodeString pattern;
    for (int i = 0; i < 50000; ++i) {
        pattern += u"\\\\Q\\\\E";
    }
    pattern += u"x";

    UErrorCode status = U_ZERO_ERROR;
    URegularExpression* re = uregex_open(pattern.getBuffer(), pattern.length(),
                                        0, nullptr, &status);
    assert(U_SUCCESS(status));
    assert(re != nullptr);

    uregex_setText(re, u"abcxyz", -1, &status);
    assert(U_SUCCESS(status));

    UBool found = uregex_find(re, 0, &status);
    assert(U_SUCCESS(status));

    int32_t start = uregex_start(re, 0, &status);
    if (found == TRUE) {
        assert(U_SUCCESS(status));
        assert(start >= 0);
    }

    uregex_close(re);
    return 0;
}
