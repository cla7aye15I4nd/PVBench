#include "unicode/ustring.h"
#include <cstdlib>
#include <cstring>

using namespace icu;

int main()
{
    const int32_t repeat = 20000;
    const int32_t srclen = repeat * 6 + 1;
    char *src = (char*)malloc(srclen);
    UChar *dest = (UChar*)malloc(sizeof(UChar) * (repeat + 1));
    if (src != NULL && dest != NULL) {
        for (int32_t i = 0; i < repeat; i++) {
            strcpy(src + (i * 6), "\\\\ud841");
        }
        u_unescape(src, dest, repeat);
        free(src);

        u_unescape("\\\\ud841\\\\x5A", dest, repeat);
        u_unescape("\\\\ud841\\\\U00050005", dest, repeat);
        u_unescape("\\\\ud841\\\\xXX", dest, repeat);
        free(dest);
    }
    return 0;
}