#include "GtpLayer.h"
#include <cassert>
#include <memory>

int main()
{
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
        new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));
    assert(gtpLayer != nullptr);

    // Header should be valid for a constructed layer
    auto* hdr = gtpLayer->getHeader();
    assert(hdr != nullptr);

    // Initial data should be valid and have non-zero length
    assert(gtpLayer->getData() != nullptr);
    size_t lenBefore = gtpLayer->getDataLen();
    assert(lenBefore > 0);

    // Modify message type and verify the change took effect
    gtpLayer->getHeader()->messageType = 0xFFu;
    assert(gtpLayer->getHeader()->messageType == 0xFFu);

    // Add an extension and verify success using isNull()
    auto ext = gtpLayer->addExtension(0x85, 0x1234);
    assert(!ext.isNull());

    // Recalculate fields and verify data remains valid
    gtpLayer->computeCalculateFields();
    assert(gtpLayer->getData() != nullptr);
    size_t lenAfter = gtpLayer->getDataLen();

    // Adding an extension should increase total layer length
    assert(lenAfter > lenBefore);

    // Header should still be accessible and messageType consistent
    assert(gtpLayer->getHeader()->messageType == 0xFFu);

    return 0;
}
