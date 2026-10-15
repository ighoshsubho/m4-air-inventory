#include <metal_stdlib>
using namespace metal;
kernel void probe(device const uint2 *a [[buffer(0)]],
                  device half2 *b [[buffer(1)]]) {
    b[0] = half2(a[0]);
}
