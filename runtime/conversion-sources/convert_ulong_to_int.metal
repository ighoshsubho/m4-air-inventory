#include <metal_stdlib>
using namespace metal;
kernel void probe(device const ulong *a [[buffer(0)]],
                  device int *b [[buffer(1)]]) {
    b[0] = int(a[0]);
}
