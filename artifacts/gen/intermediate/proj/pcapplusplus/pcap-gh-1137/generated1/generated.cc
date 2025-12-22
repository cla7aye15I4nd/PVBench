#include <cstring>
#include <cassert>
#include <string>
#include "DnsLayer.h"
#include "DnsResourceData.h"

int main(int argc, char* argv[])
{
    const std::string dnskey = "AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQ \
lNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+Sr \
DK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU=";

    pcpp::DnsLayer dnsLayer;

    uint8_t* dnskey_bytes = new uint8_t[dnskey.size()];
    assert(dnskey_bytes != nullptr);
    for (size_t i = 0; i < dnskey.size(); i++) {
        dnskey_bytes[i] = static_cast<uint8_t>(dnskey[i]);
    }

    pcpp::GenericDnsResourceData genericData(dnskey_bytes, dnskey.size());

    // Add an answer and assert success
    pcpp::DnsResource* answer = dnsLayer.addAnswer("github.com", pcpp::DNS_TYPE_DNSKEY, pcpp::DNS_CLASS_IN, 32, &genericData);
    assert(answer != nullptr);

    // After adding records, fields should be computable and data should be non-empty
    dnsLayer.computeCalculateFields();
    assert(dnsLayer.getData() != nullptr);
    size_t layerLen = dnsLayer.getDataLen();
    assert(layerLen > 0);

    // Semantic checks: counts and retrievability
    size_t answerCount = dnsLayer.getAnswerCount();
    assert(answerCount == 1);
    size_t queryCount = dnsLayer.getQueryCount();
    assert(queryCount == 0);

    // Ensure we can retrieve the just-added record by exact match
    pcpp::DnsResource* found = dnsLayer.getAnswer("github.com", true);
    assert(found != nullptr);
    assert(found == answer);

    delete[] dnskey_bytes;
    return 0;
}