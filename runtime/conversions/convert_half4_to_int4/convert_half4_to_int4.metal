#include <metal_stdlib>
using namespace metal;
kernel void probe(device const half4 *a [[buffer(0)]],
                  device int4 *b [[buffer(1)]]) {
    b[0] = int4(a[0]);
}
