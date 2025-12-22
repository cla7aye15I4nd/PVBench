#include "unicode/ustring.h"
#include <cstdlib>
#include <cstring>
#include <cassert>

using namespace icu;

int main()
{
    const int32_t repeat = 20000;
    const int32_t srclen = repeat * 6 + 1;
    // Allocate one extra byte to safely accommodate the final null terminator
    // when using overlapping strcpy in the loop below.
    char *src = (char*)malloc(srclen + 1);
    UChar *dest = (UChar*)malloc(sizeof(UChar) * (repeat + 1));
    if (src != NULL && dest != NULL) {
        for (int32_t i = 0; i < repeat; i++) {
            strcpy(src + (i * 6), "\\\\ud841");
        }
        int32_t ret1 = u_unescape(src, dest, repeat);
        assert(ret1 >= 0);
        free(src);

        int32_t ret2 = u_unescape("\\\\ud841\\\\x5A", dest, repeat);
        assert(ret2 >= 0);
        int32_t ret3 = u_unescape("\\\\ud841\\\\U00050005", dest, repeat);
        assert(ret3 >= 0);
        int32_t ret4 = u_unescape("\\\\ud841\\\\xXX", dest, repeat);
        assert(ret4 >= 0);
        free(dest);
    }
    return 0;
}