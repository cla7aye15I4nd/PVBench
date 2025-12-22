#include <cstring>
#include <cassert>
#include "DnsLayer.h"
#include "DnsResourceData.h"

int main(int argc, char* argv[])
{
    const std::string dnskey = "AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQ \
lNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+Sr \
DK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU=";

    pcpp::DnsLayer dnsLayer;
    uint8_t* dnskey_bytes = new uint8_t[dnskey.size()];
    for (size_t i = 0; i < dnskey.size(); i++) {
        dnskey_bytes[i] = dnskey[i];
    }
    pcpp::GenericDnsResourceData genericData(dnskey_bytes, dnskey.size());
    const auto* additional = dnsLayer.addAnswer("github.com", pcpp::DNS_TYPE_DNSKEY, pcpp::DNS_CLASS_IN, 32, &genericData);

    assert(additional != nullptr);  // Should not return null

    delete[] dnskey_bytes;
    return 0;
}
