#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/calendar.h"
#include "unicode/locid.h"
#include "unicode/ucal.h"
#include <iostream>

using namespace icu;

int main() {
  const char *localeID = "ar@calendar=islamic-civil";
  UErrorCode status = U_ZERO_ERROR;
  Calendar *cal = Calendar::createInstance(Locale(localeID), status);
  if (U_FAILURE(status)) {
    std::cerr << "FAIL: Calendar::createInstance for localeID " << localeID
              << ": " << u_errorName(status) << std::endl;
  } else {
    int32_t maxMonth = cal->getMaximum(UCAL_MONTH);
    int32_t maxDayOfMonth = cal->getMaximum(UCAL_DATE);
    int32_t jd, year, month, dayOfMonth;
    for (jd = 73530872; jd <= 73530876;
         jd++) { // year 202002, int32_t overflow if jd >= 73530874
      status = U_ZERO_ERROR;
      cal->clear();
      cal->set(UCAL_JULIAN_DAY, jd);
      year = cal->get(UCAL_YEAR, status);
      month = cal->get(UCAL_MONTH, status);
      dayOfMonth = cal->get(UCAL_DATE, status);
      if (U_FAILURE(status)) {
        std::cerr << "FAIL: Calendar->get YEAR/MONTH/DATE for localeID "
                  << localeID << ", julianDay " << jd << ", status "
                  << u_errorName(status) << std::endl;
      } else if (month > maxMonth || dayOfMonth > maxDayOfMonth) {
        std::cerr << "FAIL: localeID " << localeID << ", julianDay " << jd
                  << "; got year " << year << "; maxMonth " << maxMonth
                  << ", got month " << month << "; maxDayOfMonth "
                  << maxDayOfMonth << ", got dayOfMonth " << dayOfMonth
                  << std::endl;
      }
    }
    delete cal;
  }

  return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi