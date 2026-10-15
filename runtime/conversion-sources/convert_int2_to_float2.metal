#include <metal_stdlib>
using namespace metal;
kernel void probe(device const int2 *a [[buffer(0)]],
                  device float2 *b [[buffer(1)]]) {
    b[0] = float2(a[0]);
}
