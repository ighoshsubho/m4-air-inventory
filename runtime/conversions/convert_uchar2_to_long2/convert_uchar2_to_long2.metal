#include <metal_stdlib>
using namespace metal;
kernel void probe(device const uchar2 *a [[buffer(0)]],
                  device long2 *b [[buffer(1)]]) {
    b[0] = long2(a[0]);
}
