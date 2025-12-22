#include <cassert>
#include <cstring>
#include <string>
#include "DnsLayer.h"
#include "DnsResourceData.h"

int main(int argc, char* argv[])
{
    const std::string dnskey = "AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQ \
lNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+Sr \
DK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU=";

    pcpp::DnsLayer dnsLayer;

    // Prepare resource data bytes
    uint8_t* dnskey_bytes = new uint8_t[dnskey.size()];
    for (size_t i = 0; i < dnskey.size(); i++) {
        dnskey_bytes[i] = static_cast<uint8_t>(dnskey[i]);
    }
    pcpp::GenericDnsResourceData genericData(dnskey_bytes, dnskey.size());

    // Initially there should be no answers or queries
    assert(dnsLayer.getQueryCount() == 0);
    assert(dnsLayer.getAnswerCount() == 0);

    // Add an answer and verify it succeeded
    pcpp::DnsResource* answer = dnsLayer.addAnswer(
        "github.com", pcpp::DNS_TYPE_DNSKEY, pcpp::DNS_CLASS_IN, 32, &genericData);
    assert(answer != nullptr);

    // Verify counts and retrieval behavior
    assert(dnsLayer.getAnswerCount() >= 1);
    assert(dnsLayer.getQueryCount() == 0);

    pcpp::DnsResource* fetched = dnsLayer.getAnswer("github.com", true);
    assert(fetched != nullptr);

    // Partial match lookup should also succeed for exact name
    pcpp::DnsResource* fetchedPartial = dnsLayer.getAnswer("github.com", false);
    assert(fetchedPartial != nullptr);

    // Lookup of non-existing name should fail
    pcpp::DnsResource* notFound = dnsLayer.getAnswer("nonexistent.example", true);
    assert(notFound == nullptr);

    // Sanity checks on layer raw data
    assert(dnsLayer.getData() != nullptr);
    assert(dnsLayer.getDataLen() > 0);
    size_t lenBefore = dnsLayer.getDataLen();
    dnsLayer.computeCalculateFields();
    size_t lenAfter = dnsLayer.getDataLen();
    assert(lenAfter > 0);
    // Length shouldn't drop to zero after computation
    assert(lenAfter == lenBefore || lenAfter != 0);

    // Underlying resource data should be managed by the layer; free our copy
    delete[] dnskey_bytes;

    // Ensure record still retrievable after freeing external buffer
    pcpp::DnsResource* fetched2 = dnsLayer.getAnswer("github.com", true);
    assert(fetched2 != nullptr);

    return 0;
}