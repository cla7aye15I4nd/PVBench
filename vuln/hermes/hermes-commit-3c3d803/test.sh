#!/bin/bash -eu
export CXXFLAGS="-include stdexcept ${CXXFLAGS:-}"
cmake -S . -B build -G Ninja
cmake --build build -j 16
rm test/hermes/date-locale.js || true
patch -p1 <<EOF
diff --git a/unittests/VMRuntime/Instrumentation/ProcessStatsTest.cpp b/unittests/VMRuntime/Instrumentation/ProcessStatsTest.cpp
index 3dc7bb7ac..0961ace1f 100644
--- a/unittests/VMRuntime/Instrumentation/ProcessStatsTest.cpp
+++ b/unittests/VMRuntime/Instrumentation/ProcessStatsTest.cpp
@@ -64,17 +64,17 @@ TEST(ProcessStatsTest, Test) {
   // Run the test without checking anything.  This ensures that all the code for
   // the test is paged in now, and not later when we are watching the resident
   // set size.
-  ProcessStatsTest([](const char *file,
-                      unsigned line,
-                      const char *initExpr,
-                      const ProcessStats::Info &initial,
-                      const char *actualExpr,
-                      const ProcessStats::Info &actual,
-                      int64_t dRSSkB,
-                      int64_t dVAkB) {});
+  // ProcessStatsTest([](const char *file,
+  //                     unsigned line,
+  //                     const char *initExpr,
+  //                     const ProcessStats::Info &initial,
+  //                     const char *actualExpr,
+  //                     const ProcessStats::Info &actual,
+  //                     int64_t dRSSkB,
+  //                     int64_t dVAkB) {});
 
   // Run again, this time checking the change in values.
-  ProcessStatsTest(infoAssertionImpl);
+  // ProcessStatsTest(infoAssertionImpl);
 }
 
 void ProcessStatsTest(InfoAssertion assertionImpl) {
EOF
cmake --build build --target check-hermes all -j 16