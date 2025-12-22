#include "unicode/ustring.h"
#include <cstdlib>
#include <cstring>
#include <assert.h>

using namespace icu;

int main()
{
    const int32_t repeat = 20000;
    const int32_t srclen = repeat * 6 + 1;
    char *src = (char*)malloc(srclen);
    UChar *dest = (UChar*)malloc(sizeof(UChar) * (repeat + 1));
    assert(src != NULL && dest != NULL);

    for (int32_t i = 0; i < repeat; i++) {
        strcpy(src + (i * 6), "\\\\ud841");
    }

    int32_t len = u_unescape(src, dest, repeat);
    assert(len == repeat);

    for (int32_t i = 0; i < repeat; i++) {
        assert(dest[i] == 0xd841);
    }
    free(src);

    // Test case 1: \\ud841\\x5A
    u_unescape("\\\\ud841\\\\x5A", dest, repeat);
    const UChar expected1[] = {0xd841, 'Z', 0};
    assert(u_strcmp(dest, expected1) == 0);

    // Test case 2: \\ud841\\U00050005
    u_unescape("\\\\ud841\\\\U00050005", dest, repeat);
    const UChar expected2[] = {0xd841, 0xd900, 0xdc05, 0};
    assert(u_strcmp(dest, expected2) == 0);

    // Test case 3: ill-formed \\xXX should return empty string
    u_unescape("\\\\ud841\\\\xXX", dest, repeat);
    const UChar expected3[] = { 0 };
    assert(u_strcmp(dest, expected3) == 0);

    free(dest);
    return 0;
}