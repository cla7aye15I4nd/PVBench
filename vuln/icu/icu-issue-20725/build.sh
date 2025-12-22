#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/ustring.h"
#include "unicode/urename.h"
#include <cstdlib>
#include <iostream>
#include <cstring>

using namespace icu;

int main() {
    const int32_t repeat = 20000;
    const int32_t srclen = repeat * 6 + 1;
    char *src = (char*)malloc(srclen);
    UChar *dest = (UChar*) malloc(sizeof(UChar) * (repeat + 1));
    if (src == NULL || dest == NULL) {
        std::cerr << "memory allocation error" << std::endl;
        return 1;
    }
    for (int32_t i = 0; i < repeat; i++) {
      strcpy(src + (i * 6), "\\\\ud841");
    }
    int32_t len = u_unescape(src, dest, repeat);
    if (len != repeat) {
        std::cerr << "failure in u_unescape()" << std::endl;
        return 1;
    }
    for (int32_t i = 0; i < repeat; i++) {
      if (dest[i] != 0xd841) {
        std::cerr << "failure in u_unescape() return value" << std::endl;
        return 1;
      }
    }
    free(src);

    // A few simple test cases to make sure that the code recovers properly
    u_unescape("\\\\ud841\\\\x5A", dest, repeat);
    const UChar expected1[] = {0xd841, 'Z', 0};
    if (u_strcmp(dest, expected1)!=0) {
        std::cerr << "u_unescape() should return u\\"\\\\ud841Z\\" but got " << dest << std::endl;
        return 1;
    }

    u_unescape("\\\\ud841\\\\U00050005", dest, repeat);
    const UChar expected2[] = {0xd841, 0xd900, 0xdc05, 0};
    if (u_strcmp(dest, expected2)!=0) {
        std::cerr << "u_unescape() should return u\\"\\\\ud841\\\\ud900\\\\udc05\\" "
                  << "but got " << dest << std::endl;
        return 1;
    }

    // \\\\xXX is ill-formed. The documentation states:
    // If an escape sequence is ill-formed, this method returns an empty string.
    u_unescape("\\\\ud841\\\\xXX", dest, repeat);
    const UChar expected3[] = { 0 };
    if (u_strcmp(dest, expected3)!=0) {
        std::cerr << "u_unescape() should return empty string" << std::endl;
        return 1;
    }

    free(dest);
    
    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi