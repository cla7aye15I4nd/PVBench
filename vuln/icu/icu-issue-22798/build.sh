#!/bin/bash -eu
./icu4c/source/runConfigureICU Linux --prefix="$PWD/install" --enable-shared --enable-static --enable-debug
make -j32
make install

cat <<EOF > poc.cpp
#include "unicode/locid.h"
#include "unicode/msgfmt.h"
#include "unicode/utypes.h"
#include <cstdlib>
#include <iostream>

using namespace icu;

int main() {
  // Test deep nested choice will not cause stack overflow but return error
  // instead.
  UErrorCode status = U_ZERO_ERROR;
  UnicodeString pattern;
  constexpr static int testNestedLevel = 30000;
  for (int i = 0; i < testNestedLevel; i++) {
    pattern += u"A{0,choice,0#";
  }
  pattern += u"text";
  for (int i = 0; i < testNestedLevel; i++) {
    pattern += u"}a";
  }
  MessageFormat msg(pattern, status);
  if (U_FAILURE(status)) {
    std::cout << "Deep nested choice should cause error but not crash"
              << std::endl;
  }
  return 0;
}
EOF

if [ ! -z "${CXX:-}" ]; then
    ${CXX} ${CXXFLAGS} -I install/include -L install/lib -l icuuc -l icui18n -l icudata -Wl,-rpath,install/lib -o poc poc.cpp
fi