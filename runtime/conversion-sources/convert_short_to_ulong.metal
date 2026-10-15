#include <metal_stdlib>
using namespace metal;
kernel void probe(device const short *a [[buffer(0)]],
                  device ulong *b [[buffer(1)]]) {
    b[0] = ulong(a[0]);
}
