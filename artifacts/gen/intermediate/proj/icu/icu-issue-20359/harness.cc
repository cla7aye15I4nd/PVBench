#include "unicode/uregex.h"
#include "unicode/ustring.h"

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
    uregex_setText(re, u"abcxyz", -1, &status);
    uregex_find(re, 0, &status);
    uregex_start(re, 0, &status);
    uregex_close(re);
    return 0;
}