#include <metal_stdlib>
using namespace metal;
kernel void probe(device const ulong4 *a [[buffer(0)]],
                  device half4 *b [[buffer(1)]]) {
    b[0] = half4(a[0]);
}
