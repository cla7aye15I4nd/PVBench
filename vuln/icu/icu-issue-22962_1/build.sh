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
    LocalPointer<Calendar> cal(Calendar::createInstance(Locale("en@calendar=uddhist"), status), status);
    if (U_FAILURE(status)) {
        std::cout << "Should return failure" << std::endl;
    }
    cal->clear();
    cal->set(UCAL_WEEK_OF_YEAR, 1666136);
    cal->set(UCAL_YEAR, -1887379272);
    cal->fieldDifference(
        261830011167902373443927125260580558779842815957727840993886210772873194951140935848493861585917165011373697198856398176256.000000,
        UCAL_YEAR_WOY, status);
    if (U_FAILURE(status)) {
        std::cout << "Should return falure" << std::endl;
    }

    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi