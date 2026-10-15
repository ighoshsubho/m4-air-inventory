#include <metal_stdlib>
using namespace metal;
kernel void probe(device const long *a [[buffer(0)]],
                  device uchar *b [[buffer(1)]]) {
    b[0] = uchar(a[0]);
}
