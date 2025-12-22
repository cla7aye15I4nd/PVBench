#include "unicode/ustring.h"
#include <cstdlib>
#include <cstring>
#include <cassert>

using namespace icu;

int main()
{
    const int32_t repeat = 20000;
    // Fix buffer sizing to match the actual length of "\\\\ud841" which is 7 bytes (without NUL)
    const int32_t srclen = repeat * 7 + 1;
    char *src = (char*)malloc(srclen);
    UChar *dest = (UChar*)malloc(sizeof(UChar) * (repeat + 1));
    if (src != NULL && dest != NULL) {
        for (int32_t i = 0; i < repeat; i++) {
            strcpy(src + (i * 7), "\\\\ud841");
        }
        int32_t r1 = u_unescape(src, dest, repeat);
        assert(r1 >= 0);
        free(src);

        int32_t r2 = u_unescape("\\\\ud841\\\\x5A", dest, repeat);
        assert(r2 >= 0);
        int32_t r3 = u_unescape("\\\\ud841\\\\U00050005", dest, repeat);
        assert(r3 >= 0);
        int32_t r4 = u_unescape("\\\\ud841\\\\xXX", dest, repeat);
        assert(r4 >= 0);
        free(dest);
    }
    return 0;
}