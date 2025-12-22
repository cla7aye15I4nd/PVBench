#include <cassert>
#include <memory>
#include "GtpLayer.h"

int main()
{
    // Create GTPv1 layer
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
        new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));
    assert(gtpLayer != nullptr);

    // Header should be valid
    auto* hdr = gtpLayer->getHeader();
    assert(hdr != nullptr);

    // Data pointer and length should be valid and at least the size of the header
    assert(gtpLayer->getData() != nullptr);
    assert(gtpLayer->getDataLen() >= sizeof(*hdr));

    // Mutate header: set message type to 0xFF and verify
    gtpLayer->getHeader()->messageType = 0xFF;
    assert(gtpLayer->getHeader()->messageType == 0xFF);

    // Recalculate fields and ensure layer remains valid
    gtpLayer->computeCalculateFields();
    assert(gtpLayer->getHeader() != nullptr);
    assert(gtpLayer->getData() != nullptr);
    assert(gtpLayer->getDataLen() >= sizeof(*hdr));

    // Add an extension and verify success using isNull()
    size_t lenBefore = gtpLayer->getDataLen();
    auto ext = gtpLayer->addExtension(0x85, 0x1234);
    assert(!ext.isNull());

    // After adding extension the header pointer may change due to reallocation, but must remain valid
    assert(gtpLayer->getHeader() != nullptr);
    assert(gtpLayer->getData() != nullptr);
    size_t lenAfter = gtpLayer->getDataLen();
    assert(lenAfter > lenBefore);  // Semantic check: extension should increase packet size

    return 0;
}
