#include <metal_stdlib>
using namespace metal;
kernel void probe(device const uint4 *a [[buffer(0)]],
                  device ulong4 *b [[buffer(1)]]) {
    b[0] = ulong4(a[0]);
}
