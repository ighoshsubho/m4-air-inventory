#include <metal_stdlib>
using namespace metal;
kernel void probe(device const ushort *a [[buffer(0)]],
                  device uint *b [[buffer(1)]]) {
    b[0] = uint(a[0]);
}
