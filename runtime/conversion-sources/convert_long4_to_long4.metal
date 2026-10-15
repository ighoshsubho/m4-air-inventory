#include <metal_stdlib>
using namespace metal;
kernel void probe(device const long4 *a [[buffer(0)]],
                  device long4 *b [[buffer(1)]]) {
    b[0] = long4(a[0]);
}
