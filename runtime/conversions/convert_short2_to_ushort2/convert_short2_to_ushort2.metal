#include <metal_stdlib>
using namespace metal;
kernel void probe(device const short2 *a [[buffer(0)]],
                  device ushort2 *b [[buffer(1)]]) {
    b[0] = ushort2(a[0]);
}
