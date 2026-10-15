#include <metal_stdlib>
using namespace metal;
kernel void probe(device const ushort2 *a [[buffer(0)]],
                  device short2 *b [[buffer(1)]]) {
    b[0] = short2(a[0]);
}
