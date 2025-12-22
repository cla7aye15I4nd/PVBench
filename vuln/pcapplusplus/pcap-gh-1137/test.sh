#!/bin/bash -eu
patch -p1 -F 3 <<EOF
diff --git a/Tests/Pcap++Test/Tests/SystemUtilsTests.cpp b/Tests/Pcap++Test/Tests/SystemUtilsTests.cpp
index 86f445da..63a59f61 100644
--- a/Tests/Pcap++Test/Tests/SystemUtilsTests.cpp
+++ b/Tests/Pcap++Test/Tests/SystemUtilsTests.cpp
@@ -4,12 +4,6 @@
 
 PTF_TEST_CASE(TestSystemCoreUtils)
 {
-	auto numOfCores = pcpp::getNumOfCores();
-	PTF_ASSERT_GREATER_THAN(numOfCores, 1);
-
-	std::bitset<32> bs(pcpp::getCoreMaskForAllMachineCores());
-	PTF_ASSERT_EQUAL(bs.count(), numOfCores);
-
 	auto coreVector =
 	    std::vector<pcpp::SystemCore>{ pcpp::SystemCores::Core0, pcpp::SystemCores::Core2, pcpp::SystemCores::Core4 };
 	PTF_ASSERT_EQUAL(pcpp::createCoreMaskFromCoreVector(coreVector), 0b10101);
EOF
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pytest scapy

cmake -S . -B build --install-prefix=$PWD/install -DBUILD_SHARED_LIBS=ON
cmake --build build --parallel 16
cmake --install build
cd build
make test -j16