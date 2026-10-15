#include <metal_stdlib>
using namespace metal;
kernel void probe(device const float2 *a [[buffer(0)]],
                  device char2 *b [[buffer(1)]]) {
    b[0] = char2(a[0]);
}
