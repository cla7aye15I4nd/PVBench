#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/locid.h"
#include "unicode/utypes.h"
#include "unicode/calendar.h"
#include <iostream>
#include <cstdlib>

using namespace icu;


int main() {
    UErrorCode status = U_ZERO_ERROR;
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=chinese"), status), status);
    if (U_FAILURE(status)) {
        std::cout << "Should return failure" << std::endl;
    }
    cal->add(UCAL_DAY_OF_WEEK_IN_MONTH, 1661092210, status);
    cal->add(UCAL_MINUTE, -1330638081, status);
    cal->add(UCAL_MONTH, 643194, status);
    if (U_FAILURE(status)) {
        std::cout << "Should return falure" << std::endl;
    }

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi