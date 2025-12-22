#include <cassert>
#include <memory>
#include "GtpLayer.h"

int main()
{
    auto gtpLayer = std::unique_ptr<pcpp::GtpV1Layer>(
        new pcpp::GtpV1Layer(pcpp::GtpV1MessageType::GtpV1_VersionNotSupported, 0x12345678, true, 1, false, 0));
    assert(gtpLayer != nullptr);

    // Header should be valid for a constructed layer
    auto* hdr = gtpLayer->getHeader();
    assert(hdr != nullptr);

    // Data pointer should be valid and have non-zero length
    assert(gtpLayer->getData() != nullptr);
    size_t lenBefore = gtpLayer->getDataLen();
    assert(lenBefore > 0);

    // Modify message type and verify
    gtpLayer->getHeader()->messageType = 0xFF;
    assert(gtpLayer->getHeader()->messageType == 0xFF);

    // Add extension and verify success using isNull()
    auto ext = gtpLayer->addExtension(0x85, 0x1234);
    assert(!ext.isNull());

    // Header pointer may change after addExtension due to reallocation; ensure it's still valid
    assert(gtpLayer->getHeader() != nullptr);

    // Data length should increase after adding an extension
    size_t lenAfter = gtpLayer->getDataLen();
    assert(lenAfter > lenBefore);

    // Recalculate fields and verify data remains valid
    gtpLayer->computeCalculateFields();
    assert(gtpLayer->getData() != nullptr);
    assert(gtpLayer->getDataLen() > 0);

    return 0;
}
