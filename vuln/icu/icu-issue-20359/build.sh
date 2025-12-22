#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/uregex.h"
#include "unicode/ustring.h"
#include <iostream>

using namespace icu;

int main() {
    // Test for stack overflow bug fix with many adjacent \Q\E pairs
    UnicodeString pattern;
    for (int i = 0; i < 50000; ++i) {
        pattern += u"\\\\Q\\\\E";
    }
    pattern += u"x";
    
    UErrorCode status = U_ZERO_ERROR;
    URegularExpression* re = uregex_open(pattern.getBuffer(), pattern.length(),
                                        0, nullptr, &status);
    
    if (U_FAILURE(status)) {
        std::cerr << "Error: " << u_errorName(status) << std::endl;
        return 1;
    }
    
    uregex_setText(re, u"abcxyz", -1, &status);
    if (U_FAILURE(status)) {
        uregex_close(re);
        return 1;
    }
    
    UBool found = uregex_find(re, 0, &status);
    if (U_SUCCESS(status) && found) {
        int32_t start = uregex_start(re, 0, &status);
        if (start == 3) {
            std::cout << "Test passed" << std::endl;
        } else {
            std::cout << "Test failed" << std::endl;
        }
    }
    
    uregex_close(re);
    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi