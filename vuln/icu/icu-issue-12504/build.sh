#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include <iostream>
#include <unicode/calendar.h>
#include <unicode/locid.h>
#include <unicode/unistr.h>

using namespace icu;

int main() {
    const char* localeID = "bs_Cyrl@calendar=persian";
    UErrorCode status = U_ZERO_ERROR;
    Calendar* cal = Calendar::createInstance(Locale(localeID), status);
    
    if (U_FAILURE(status)) {
        std::cerr << "Error creating calendar: " << u_errorName(status) << std::endl;
        return 1;
    }
    
    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t maxDayOfMonth = cal->getMaximum(UCAL_DATE);
    int32_t jd, month, dayOfMonth;
    
    for (jd = 67023580; jd <= 67023584; jd++) {
        status = U_ZERO_ERROR;
        cal->clear();
        cal->set(UCAL_JULIAN_DAY, jd);
        month = cal->get(UCAL_MONTH, status);
        dayOfMonth = cal->get(UCAL_DATE, status);
        
        if (U_FAILURE(status)) {
            std::cerr << "Error getting date for Julian day " << jd << std::endl;
        } else if (month > maxMonth || dayOfMonth > maxDayOfMonth) {
            std::cerr << "Invalid date for Julian day " << jd 
                      << ": month=" << month << ", day=" << dayOfMonth << std::endl;
        }
    }
    
    delete cal;
    return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi